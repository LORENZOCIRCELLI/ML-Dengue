"""V1: previsão de crescimento de casos, três arquiteturas e quatro horizontes."""
from pathlib import Path
import copy
import hashlib
import json
import platform
import importlib.metadata

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
from torch import nn
import shap
from captum.attr import Saliency, IntegratedGradients
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, roc_curve, log_loss)

SEEDS = [42, 123, 2025, 7, 99]
HORIZONS = [4, 8, 12, 16]
FEATURES = ['casos_dengue', 'temperatura_media', 'umidade_media', 'chuva_total', 'semana_sin', 'semana_cos']
MODELS = {'random_forest': 'Random Forest', 'rnn': 'RNN', 'lstm': 'LSTM'}
METRICS = {'f1': 'F1', 'precision': 'Precisão', 'recall': 'Recall', 'roc_auc': 'ROC-AUC',
           'pr_auc': 'PR-AUC (Average Precision)', 'accuracy': 'Acurácia'}
SPLITS = {'treino': 'Treino', 'validacao': 'Validação', 'teste': 'Teste histórico'}
COLORS = {'treino': '#2563EB', 'validacao': '#D97706', 'teste': '#059669',
          'random_forest': '#2563EB', 'rnn': '#D97706', 'lstm': '#059669',
          'shap': '#7C3AED', 'saliency': '#7C3AED', 'integrated_gradients': '#0891B2', 'gini': '#7C3AED'}
CONFIG = {'version': 'v1.0.0', 'seeds': SEEDS, 'horizons_weeks': HORIZONS,
    'sequence_length': 12, 'growth_fraction': .5, 'baseline_weeks': 4, 'decision_threshold': .5,
    'features': FEATURES, 'availability_lag_weeks': 1,
    'train_end': '2019-12-22', 'validation_end': '2022-12-25',
    'forest_tree_counts': [25, 50, 100, 200], 'forest_max_depth': 6, 'forest_min_samples_leaf': 2,
    'network_hidden_size': 24, 'learning_rate': .003, 'max_epochs': 150, 'patience': 20,
    'network_selection': 'menor perda BCE de validação', 'forest_selection': 'maior F1 de validação',
    'ensemble': 'média das saídas das cinco sementes predefinidas; nenhuma semente é escolhida',
    'pr_auc_definition': 'sklearn.average_precision_score',
    'target': 'casos(t+h) >= 1,5 × média de casos(t−4 ... t−1)',
    'historical_evaluation': 'retrospectiva e exploratória; período já examinado no desenvolvimento',
    'refit_after_evaluation': False}
CRITERION = ('Aumento de pelo menos 50% em relação à média das quatro semanas '
             'anteriores à emissão da previsão.')
WARNING = ('As previsões podem errar devido a particularidades locais, '
           'mudanças na transmissão, no clima e nos registros de casos. Não devem ser tomadas '
           'como verdade absoluta nem como confirmação de surto.')
ACCURACY_NOTE = ('A taxa de acerto descreve o desempenho histórico no conjunto avaliado; '
                 'não é a probabilidade de esta previsão individual estar correta.')


def records(frame):
    return json.loads(frame.replace([np.inf, -np.inf], np.nan).to_json(
        orient='records', force_ascii=False, double_precision=15, date_format='iso'))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def table(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path.with_suffix('.csv'), index=False)
    write_json(path.with_suffix('.json'), records(frame))


def figure(path, fig):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in ['png', 'svg']:
        fig.savefig(path.with_suffix('.'+ext), dpi=150, bbox_inches='tight')
    plt.close(fig)


def scores(y, probability):
    pred = (np.asarray(probability) >= .5).astype(int)
    return {'f1': f1_score(y, pred, zero_division=0), 'precision': precision_score(y, pred, zero_division=0),
        'recall': recall_score(y, pred, zero_division=0), 'roc_auc': roc_auc_score(y, probability),
        'pr_auc': average_precision_score(y, probability), 'accuracy': accuracy_score(y, pred),
        'n_samples': len(y), 'n_positive': int(np.sum(y)), 'predicted_positive': int(pred.sum())}


class SequenceClassifier(nn.Module):
    def __init__(self, kind):
        super().__init__()
        layer = nn.RNN if kind == 'rnn' else nn.LSTM
        self.recurrent = layer(input_size=6, hidden_size=24, num_layers=1, batch_first=True)
        self.output = nn.Linear(24, 1)

    def forward(self, x):
        sequence, _ = self.recurrent(x.reshape(-1, 12, 6))
        return self.output(sequence[:, -1, :]).squeeze(-1)


class ProbabilityEnsemble(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)

    def forward(self, x):
        return torch.stack([torch.sigmoid(m(x)) for m in self.models]).mean(dim=0)


def load_data(project_root):
    path = Path(project_root)/'data/dataset/processado/base_modelagem_dengue_dataset.xlsx'
    df = pd.read_excel(path)
    df['dt_pri_sem'] = pd.to_datetime(df.dt_pri_sem)
    df = df.sort_values('dt_pri_sem').reset_index(drop=True)
    assert not df.dt_pri_sem.duplicated().any()
    assert df.dt_pri_sem.diff().dropna().eq(pd.Timedelta(weeks=1)).all()
    features = pd.DataFrame({'casos_dengue': df['n dengue'].astype(float),
        'temperatura_media': df.media_temperatura_semana, 'umidade_media': df.media_umidade_semana,
        'chuva_total': df.chuva_total_mm,
        'semana_sin': np.sin(2*np.pi*df.semana_epidemiologica/52),
        'semana_cos': np.cos(2*np.pi*df.semana_epidemiologica/52)})
    assert np.isfinite(features.to_numpy()).all() and (features.casos_dengue >= 0).all()
    audit = {'n_weeks': len(df), 'first_week': df.dt_pri_sem.iloc[0].date().isoformat(),
        'last_week': df.dt_pri_sem.iloc[-1].date().isoformat(), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return df, features, audit


def prepare_horizon(df, features, horizon, directory):
    available = features.shift(1)
    cases = features.casos_dengue
    baseline = cases.shift(1).rolling(4).mean()
    origins = np.arange(15, len(df)-horizon)
    samples = pd.DataFrame({'sample_id': origins, 'data_emissao': df.dt_pri_sem.iloc[origins].to_numpy(),
        'data_alvo': df.dt_pri_sem.iloc[origins+horizon].to_numpy(),
        'media_referencia': baseline.iloc[origins].to_numpy(),
        'casos_futuros': cases.iloc[origins+horizon].to_numpy()})
    samples['target'] = (samples.casos_futuros >= 1.5*samples.media_referencia).astype(int)
    samples['split'] = 'descartado_fronteira'
    samples.loc[samples.data_alvo <= pd.Timestamp(CONFIG['train_end']), 'split'] = 'treino'
    samples.loc[(samples.data_emissao > pd.Timestamp(CONFIG['train_end'])) &
                (samples.data_alvo <= pd.Timestamp(CONFIG['validation_end'])), 'split'] = 'validacao'
    samples.loc[samples.data_emissao > pd.Timestamp(CONFIG['validation_end']), 'split'] = 'teste'
    table(directory/'data/amostras_incluindo_fronteiras', samples)
    samples = samples[samples.split != 'descartado_fronteira'].reset_index(drop=True)
    raw = np.stack([available.iloc[i-11:i+1].to_numpy() for i in samples.sample_id])
    assert np.isfinite(raw).all()
    scaler = StandardScaler().fit(raw[samples.split.eq('treino')].reshape(-1, 6))
    scaled = scaler.transform(raw.reshape(-1,6)).reshape(len(raw),72).astype(np.float32)
    X, y, split_samples = {}, {}, {}
    names = [f'{col}__tmenos{12-offset}' for offset in range(12) for col in FEATURES]
    for split in SPLITS:
        mask = samples.split.eq(split).to_numpy()
        X[split], y[split] = scaled[mask], samples.loc[mask,'target'].to_numpy(dtype=np.int64)
        split_samples[split] = samples.loc[mask].reset_index(drop=True)
        assert set(y[split]) == {0,1}
        frame = pd.DataFrame(X[split], columns=names)
        frame.insert(0,'sample_id',split_samples[split].sample_id.to_numpy())
        frame['target'] = y[split]
        table(directory/f'data/{split}_padronizado',frame)
    assert split_samples['treino'].data_alvo.max() < split_samples['validacao'].data_emissao.min()
    assert split_samples['validacao'].data_alvo.max() < split_samples['teste'].data_emissao.min()
    last = len(df)-1
    latest_raw = available.iloc[last-11:last+1].to_numpy()
    latest = scaler.transform(latest_raw).reshape(1,72).astype(np.float32)
    forecast = {'dataReferencia': df.dt_pri_sem.iloc[-1].date().isoformat(),
        'dataAlvo': (df.dt_pri_sem.iloc[-1]+pd.Timedelta(weeks=horizon)).date().isoformat(),
        'mediaCasosReferencia': float(baseline.iloc[-1]),
        'limiteCasosAumento': float(1.5*baseline.iloc[-1]), 'horizonteSemanas': horizon}
    table(directory/'data/particoes',samples)
    summary = samples.groupby('split',sort=False).agg(amostras=('target','size'),positivos=('target','sum'),
        prevalencia=('target','mean'),primeiro_alvo=('data_alvo','min'),ultimo_alvo=('data_alvo','max')).reset_index()
    table(directory/'data/resumo_particoes',summary)
    joblib.dump(scaler,directory/'scaler.joblib')
    return X,y,split_samples,names,latest,forecast


def train(kind,X,y,directory):
    models, histories, selections = [],[],[]
    artifact = directory/'artifacts'
    artifact.mkdir(parents=True,exist_ok=True)
    for seed in SEEDS:
        torch.manual_seed(seed)
        np.random.seed(seed)
        if kind == 'random_forest':
            best = -np.inf
            for n in CONFIG['forest_tree_counts']:
                candidate = RandomForestClassifier(n_estimators=n,max_depth=6,min_samples_leaf=2,
                    class_weight='balanced',random_state=seed,n_jobs=1).fit(X['treino'],y['treino'])
                for split in ['treino','validacao']:
                    prob = candidate.predict_proba(X[split])[:,1]
                    metric = scores(y[split],prob)
                    histories.append({'seed':seed,'step':n,'split':split,
                        'loss':log_loss(y[split],prob,labels=[0,1]),**metric})
                    if split == 'validacao' and metric['f1'] > best:
                        best=metric['f1'];selected=n;model=copy.deepcopy(candidate)
            joblib.dump(model,artifact/f'seed_{seed}.joblib')
            selections.append({'seed':seed,'selected_step':selected,'selection':'validation_f1'})
        else:
            model = SequenceClassifier(kind)
            optimizer = torch.optim.Adam(model.parameters(),lr=.003)
            criterion = nn.BCEWithLogitsLoss()
            tensors = {s:torch.tensor(X[s]) for s in ['treino','validacao']}
            targets = {s:torch.tensor(y[s],dtype=torch.float32) for s in tensors}
            best_loss,stale,best_state = np.inf,0,None
            for epoch in range(1,151):
                model.train();optimizer.zero_grad()
                loss = criterion(model(tensors['treino']),targets['treino'])
                loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
                model.eval()
                with torch.no_grad():
                    for split in tensors:
                        logits = model(tensors[split]);prob=torch.sigmoid(logits).numpy()
                        val_loss=criterion(logits,targets[split]).item()
                        histories.append({'seed':seed,'step':epoch,'split':split,'loss':val_loss,**scores(y[split],prob)})
                if val_loss < best_loss-1e-8:
                    best_loss=val_loss;selected=epoch;best_state=copy.deepcopy(model.state_dict());stale=0
                else:stale+=1
                if stale>=20:break
            model.load_state_dict(best_state);model.eval()
            torch.save({'state_dict':best_state,'model_type':kind,'seed':seed,'selected_epoch':selected,
                'stopped_epoch':epoch,'input_size':6,'hidden_size':24,'sequence_length':12,
                'selected_validation_loss':best_loss},artifact/f'seed_{seed}.pt')
            selections.append({'seed':seed,'selected_step':selected,'stopped_epoch':epoch,
                'selection':'validation_bce_loss','selected_loss':best_loss})
        models.append(model)
    table(directory/'metrics/historico_treinamento',pd.DataFrame(histories))
    table(directory/'metrics/selecao_por_semente',pd.DataFrame(selections))
    return models,pd.DataFrame(histories)


def predict(kind,models,X):
    if kind=='random_forest':return np.array([m.predict_proba(X)[:,1] for m in models])
    with torch.no_grad():return np.array([torch.sigmoid(m(torch.tensor(X))).numpy() for m in models])


def exploratory(X,y,directory,title):
    """Descrições dos atributos somente no treino; não seleciona variáveis."""
    from matplotlib.cbook import boxplot_stats
    last=pd.DataFrame(X['treino'].reshape(-1,12,6)[:,-1,:],columns=FEATURES)
    table(directory/'eda/estatisticas_treino',last.describe().T.rename_axis('feature').reset_index())
    missing=pd.DataFrame({'feature':FEATURES,'missing_count':last.isna().sum().to_numpy()})
    table(directory/'eda/valores_ausentes_treino',missing)
    rows=[]
    for split in SPLITS:
        counts=np.bincount(y[split],minlength=2);p=counts/counts.sum()
        rows.extend({'split':split,'class':i,'count':int(counts[i]),'proportion':float(p[i]),
                     'gini_impurity':float(1-np.sum(p**2))} for i in [0,1])
    table(directory/'eda/classes_e_gini',pd.DataFrame(rows))
    fig,axes=plt.subplots(2,3,figsize=(13,8));hist=[]
    for ax,col in zip(axes.flat,FEATURES):
        count,edges=np.histogram(last[col],bins=20);centers=(edges[1:]+edges[:-1])/2
        ax.bar(centers,count,width=np.diff(edges)*.95,color=COLORS['treino'])
        ax.set(title=col,xlabel='Valor padronizado (DP)',ylabel='Semanas')
        hist.extend({'feature':col,'left':float(a),'right':float(b),'center':float(c),'count':int(n)}
                    for a,b,c,n in zip(edges[:-1],edges[1:],centers,count))
    fig.suptitle(title+' — distribuições no treino',fontsize=14)
    figure(directory/'eda/figures/histogramas',fig);table(directory/'eda/histogramas',pd.DataFrame(hist))
    corr=last.corr();fig,ax=plt.subplots(figsize=(9,8));im=ax.imshow(corr,cmap='RdBu_r',vmin=-1,vmax=1)
    ax.set(xticks=range(6),yticks=range(6),xticklabels=FEATURES,yticklabels=FEATURES,
        title=title+' — correlação no treino',xlabel='Atributo',ylabel='Atributo')
    ax.tick_params(axis='x',rotation=90);ax.grid(False);fig.colorbar(im,ax=ax,label='Pearson (−1 a 1)')
    figure(directory/'eda/figures/correlacoes',fig)
    table(directory/'eda/correlacoes',pd.DataFrame([{'feature_x':a,'feature_y':b,'correlation':float(corr.loc[b,a])} for b in FEATURES for a in FEATURES]))
    boxrows=[];outliers=[];fig,axes=plt.subplots(1,2,figsize=(13,6),sharex=True)
    for ax,cls in zip(axes,[0,1]):
        stats=[]
        for col in FEATURES:
            stat=boxplot_stats(last.loc[y['treino']==cls,col],whis=1.5)[0];stat['label']=col;stats.append(stat)
            boxrows.append({'feature':col,'class':cls,**{k:float(stat[k]) for k in ['med','q1','q3','whislo','whishi']}})
            outliers.extend({'feature':col,'class':cls,'value':float(v)} for v in stat['fliers'])
        ax.bxp(stats,orientation='horizontal');ax.set(title=f'Treino — classe {cls}',xlabel='Valor padronizado (DP)',ylabel='Atributo')
    figure(directory/'eda/figures/boxplots',fig)
    table(directory/'eda/boxplots',pd.DataFrame(boxrows))
    table(directory/'eda/outliers',pd.DataFrame(outliers,columns=['feature','class','value']))


def evaluate(kind,models,X,y,samples,directory,title,history):
    metrics,per_seed,probabilities,roc_rows,matrices = [],[],{},[],{}
    for split in SPLITS:
        individual = predict(kind,models,X[split]);prob=individual.mean(axis=0)
        probabilities[split]=prob
        metrics.append({'split':split,**scores(y[split],prob)})
        for seed,p in zip(SEEDS,individual):per_seed.append({'split':split,'seed':seed,**scores(y[split],p)})
        frame=samples[split].copy();frame['escore_aumento']=prob;frame['prediction']=(prob>=.5).astype(int)
        for seed,p in zip(SEEDS,individual):frame[f'escore_seed_{seed}']=p
        table(directory/f'data/previsoes_{split}',frame)
        cm=confusion_matrix(y[split],prob>=.5,labels=[0,1])
        matrices[split]={'rotulos':['Sem aumento ≥ 50%','Aumento ≥ 50%'],'valores':cm.tolist()}
        fpr,tpr,thresholds=roc_curve(y[split],prob)
        roc_rows.extend({'split':split,'false_positive_rate':float(a),'true_positive_rate':float(b),
            'threshold':float(c) if np.isfinite(c) else None} for a,b,c in zip(fpr,tpr,thresholds))
    frame=pd.DataFrame(metrics)
    table(directory/'metrics/metricas_ensemble',frame)
    table(directory/'metrics/metricas_por_semente',pd.DataFrame(per_seed))
    table(directory/'metrics/curvas_roc',pd.DataFrame(roc_rows))
    write_json(directory/'metrics/matrizes_confusao.json',matrices)
    fig,axes=plt.subplots(2,3,figsize=(15,9))
    for ax,(metric,label) in zip(axes.flat,METRICS.items()):
        bars=ax.bar([SPLITS[s] for s in frame.split],frame[metric],color=[COLORS[s] for s in frame.split])
        ax.bar_label(bars,fmt='%.3f',padding=3);ax.set(title=label,ylabel='Escore (0–1)',ylim=(0,1.13))
        ax.tick_params(axis='x',rotation=15)
    fig.suptitle(title+' — métricas do ensemble',fontsize=15)
    figure(directory/'figures/01_metricas',fig)
    fig,axes=plt.subplots(2,3,figsize=(15,9))
    for ax,(metric,label) in zip(axes.flat,METRICS.items()):
        for split in ['treino','validacao']:
            h=history[history.split==split].groupby('step')[metric].mean()
            ax.plot(h.index,h,color=COLORS[split],label=SPLITS[split])
        ax.set(title=label,xlabel='Árvores' if kind=='random_forest' else 'Época',ylabel='Escore (0–1)',ylim=(0,1.03));ax.legend(fontsize=8)
    fig.suptitle(title+' — média das sementes ainda em treinamento',fontsize=14)
    figure(directory/'figures/02_treinamento',fig)
    fig,ax=plt.subplots(figsize=(7,6))
    for split in SPLITS:
        a,b,_=roc_curve(y[split],probabilities[split]);auc=frame.loc[frame.split==split,'roc_auc'].iloc[0]
        ax.plot(a,b,color=COLORS[split],label=f'{SPLITS[split]} (AUC={auc:.3f})')
    ax.plot([0,1],[0,1],'--',color='#64748B');ax.set(title=title+' — ROC',xlabel='Falsos positivos (0–1)',ylabel='Recall (0–1)');ax.legend()
    figure(directory/'figures/03_roc',fig)
    cm=np.array(matrices['teste']['valores']);fig,ax=plt.subplots(figsize=(6,5));im=ax.imshow(cm,cmap='Blues')
    for (i,j),value in np.ndenumerate(cm):ax.text(j,i,str(value),ha='center',va='center',color='white' if value>cm.max()/2 else '#0F172A')
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Sem aumento','Aumento'],yticklabels=['Sem aumento','Aumento'],
        title=title+' — teste histórico',xlabel='Classe prevista',ylabel='Classe real');ax.grid(False)
    fig.colorbar(im,ax=ax,label='Semanas (contagem)');figure(directory/'figures/04_confusao',fig)
    return frame,probabilities,matrices,roc_rows


def explain(kind,models,X,latest,names,samples,directory,title):
    combined=np.concatenate([X['teste'],latest])
    methods,diagnostics={},{}
    if kind=='random_forest':
        values=[];bases=[]
        for model in models:
            explainer=shap.TreeExplainer(model,model_output='raw',feature_perturbation='tree_path_dependent')
            raw=explainer.shap_values(combined,check_additivity=True)
            values.append(np.asarray(raw[1]) if isinstance(raw,list) else np.asarray(raw)[:,:,1])
            bases.append(float(np.asarray(explainer.expected_value)[1]))
        attributions=np.mean(values,axis=0);base=float(np.mean(bases))
        error=np.abs(base+attributions.sum(axis=1)-predict(kind,models,combined).mean(axis=0))
        assert error.max()<1e-5
        methods['shap']=attributions
        diagnostics['shap']={'valorBase':base,'maiorErroAditividade':float(error.max())}
        gini=np.array([m.feature_importances_ for m in models])
        frame=pd.DataFrame({'feature':names,'importance':gini.mean(axis=0),'std_between_seeds':gini.std(axis=0,ddof=1)}).sort_values('importance',ascending=False)
        table(directory/'explainability/gini_importancia',frame)
        top=frame.head(15).iloc[::-1];fig,ax=plt.subplots(figsize=(10,7));ax.barh(top.feature,top.importance,xerr=top.std_between_seeds,color=COLORS['gini'])
        ax.set(title=title+' — importância Gini',xlabel='Importância normalizada (0–1); DP entre sementes',ylabel='Atributo e defasagem')
        figure(directory/'figures/05_gini',fig)
        diagnostics['gini']={'importancia':records(frame),'unidade':'normalizada, soma 1; DP entre sementes, não IC'}
    else:
        model=ProbabilityEnsemble(models).eval();inputs=torch.tensor(combined,requires_grad=True)
        methods['saliency']=Saliency(model).attribute(inputs,abs=False).detach().numpy()
        steps=128
        values,delta=IntegratedGradients(model).attribute(inputs,baselines=torch.zeros_like(inputs),
            n_steps=steps,internal_batch_size=len(inputs),return_convergence_delta=True)
        if delta.abs().max()>.005:
            steps=512
            values,delta=IntegratedGradients(model).attribute(inputs,baselines=torch.zeros_like(inputs),
                n_steps=steps,internal_batch_size=len(inputs),return_convergence_delta=True)
        assert np.isfinite(values.detach().numpy()).all() and delta.abs().max()<.01
        methods['integrated_gradients']=values.detach().numpy()
        with torch.no_grad():base=float(model(torch.zeros((1,72))).item())
        diagnostics['integrated_gradients']={'baseline':'zero padronizado: média do treino','valorBase':base,
            'nSteps':steps,'maiorErroCompletude':float(delta.abs().max())}
        table(directory/'explainability/convergencia_IG',pd.DataFrame({'sample_id':list(samples['teste'].sample_id)+[-1],
            'delta':delta.detach().numpy(),'is_forecast':[False]*len(X['teste'])+[True]}))
    payload={'classeExplicada':'aumento de pelo menos 50% nos casos','saidaExplicada':'média das saídas das cinco sementes (0–1)',
        'particaoGlobal':'teste histórico','atributos':names,'metodos':{},'diagnosticos':diagnostics,
        'interpretacao':'Atribuições explicam o modelo; não demonstram causalidade ou confirmam surto.'}
    for method,values in methods.items():
        assert values.shape==combined.shape and np.isfinite(values).all()
        historical=values[:-1];local=values[-1]
        global_frame=pd.DataFrame({'feature':names,'mean_absolute_attribution':np.abs(historical).mean(axis=0),
            'mean_signed_attribution':historical.mean(axis=0)}).sort_values('mean_absolute_attribution',ascending=False)
        local_frame=pd.DataFrame({'feature':names,'attribution':local,'standardized_input':latest[0]})
        individual=pd.DataFrame(historical,columns=names);individual.insert(0,'sample_id',samples['teste'].sample_id.to_numpy())
        table(directory/f'explainability/{method}_atribuicoes_teste',individual)
        table(directory/f'explainability/{method}_importancia',global_frame)
        table(directory/f'explainability/{method}_previsao',local_frame)
        grouped=historical.reshape(-1,12,6).sum(axis=1)
        global_variables=pd.DataFrame({'feature':FEATURES,'mean_absolute_attribution':np.abs(grouped).mean(axis=0),
            'mean_signed_attribution':grouped.mean(axis=0)}).sort_values('mean_absolute_attribution',ascending=False)
        table(directory/f'explainability/{method}_por_variavel',global_variables)
        unit='saída (0–1)' if method!='saliency' else 'saída (0–1) por unidade padronizada'
        payload['metodos'][method]={'unidade':unit,'importanciaGlobal':records(global_frame),
            'importanciaPorVariavel':records(global_variables),'regraAgregacao':'somar atribuições assinadas nos 12 atrasos; depois calcular média absoluta entre amostras',
            'previsao':records(local_frame),'atribuicoesTeste':records(individual)}
        top=global_frame.head(15).iloc[::-1];fig,ax=plt.subplots(figsize=(10,7));ax.barh(top.feature,top.mean_absolute_attribution,color=COLORS[method])
        ax.set(title=title+' — '+method.replace('_',' ').title(),xlabel='Atribuição absoluta média ('+unit+')',ylabel='Atributo e defasagem')
        figure(directory/f'figures/06_{method}',fig)
    write_json(directory/'explicabilidade.json',payload)
    return payload


def forecast_output(kind,horizon,models,latest,context,metrics,matrices,directory):
    score=float(predict(kind,models,latest).mean());decision=score>=.5
    historical=metrics[metrics.split=='teste'].iloc[0]
    accuracy=float(historical.accuracy);n=int(historical.n_samples)
    accuracy_text=f'{accuracy*100:.1f}'.replace('.',',')
    date=pd.Timestamp(context['dataAlvo']).strftime('%d/%m/%Y')
    text=(f'Previsão para a semana de {date}\nAumento de casos previsto: {"sim" if decision else "não"}\n'
        f'Critério: {CRITERION}\nDesempenho histórico do modelo: {accuracy_text}% de acerto em {n} semanas avaliadas.\n'
        f'Modelo experimental.\n{WARNING}\n{ACCURACY_NOTE}')
    payload={'schemaVersion':'1.0.0','versao':'v1.0.0','modelo':kind,'nomeModelo':MODELS[kind],
        **context,'aumentoCasosPrevisto':bool(decision),'resposta':'sim' if decision else 'não',
        'criterio':CRITERION,'escoreAumentoNaoCalibrado':score,'limiarDecisao':.5,
        'desempenhoHistorico':{'acuracia':accuracy,'acuraciaPercentual':accuracy*100,'semanasAvaliadas':n,
            'semanasComAumento':int(historical.n_positive),'f1':float(historical.f1),'precision':float(historical.precision),
            'recall':float(historical.recall),'rocAuc':float(historical.roc_auc),'prAuc':float(historical.pr_auc),
            'tipoAvaliacao':'retrospectiva exploratória','matrizConfusao':matrices['teste']},
        'experimental':True,'aviso':WARNING,'notaTaxaAcerto':ACCURACY_NOTE,'textoConclusao':text}
    write_json(directory/'previsao.json',payload)
    write_json(directory/'conclusao.json',{'modelo':kind,'horizonteSemanas':horizon,'dataAlvo':context['dataAlvo'],
        'texto':text,'experimental':True,'aviso':WARNING,'notaTaxaAcerto':ACCURACY_NOTE})
    (directory/'conclusao.md').write_text(text+'\n',encoding='utf-8')
    return payload


def run_study(project_root, horizons=None):
    root=Path(project_root).resolve();results=root/'v1/results';results.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':13,'figure.facecolor':'white',
        'axes.facecolor':'white','axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
    df,features,audit=load_data(root)
    table(results/'data/dataset_utilizado',pd.concat([df[['dt_pri_sem']],features],axis=1))
    write_json(results/'configuracao.json',{**CONFIG,'audit':audit,'python':platform.python_version(),
        'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','torch','captum','shap','matplotlib']}})
    all_metrics=[];catalog=[]
    for horizon in horizons or HORIZONS:
        hd=results/'horizontes'/f'{horizon:02d}_semanas';hd.mkdir(parents=True,exist_ok=True)
        X,y,samples,names,latest,context=prepare_horizon(df,features,horizon,hd)
        exploratory(X,y,hd,f'V1 — {horizon} semanas')
        for kind,name in MODELS.items():
            directory=hd/kind;directory.mkdir(exist_ok=True)
            title=f'{name} — {horizon} semanas'
            print('Treinando',title,flush=True)
            models,history=train(kind,X,y,directory)
            metric,prob,matrices,roc=evaluate(kind,models,X,y,samples,directory,title,history)
            metric_payload={'modelo':kind,'horizonteSemanas':horizon,'tipoModelo':'ensemble médio de cinco sementes',
                'metricas':records(metric),'matrizesConfusao':matrices,'curvasRoc':roc,'unidade':'escores 0–1; contagens em semanas',
                'tipoTeste':'histórico retrospectivo e exploratório','selecaoPeloTeste':False,
                'baselineSempreNegativoAcuracia':float(1-y['teste'].mean())}
            write_json(directory/'metricas.json',metric_payload)
            exp=explain(kind,models,X,latest,names,samples,directory,title)
            forecast=forecast_output(kind,horizon,models,latest,context,metric,matrices,directory)
            write_json(directory/'resultado_completo.json',{'previsao':forecast,'metricas':metric_payload,
                'explicabilidade':exp,'estilo':{'fonte':'DejaVu Sans','cores':COLORS}})
            write_json(directory/'configuracao.json',{**CONFIG,'model':kind,'horizon_weeks':horizon,'flattened_features':names,
                'units':{'cases':'casos por semana','temperature':'°C','humidity':'%','rain':'mm por semana',
                    'processed_features':'desvios padrão da média do treino','metrics':'0–1'},
                'evaluation_first_target':samples['teste'].data_alvo.min().date().isoformat(),
                'evaluation_last_target':samples['teste'].data_alvo.max().date().isoformat()})
            for row in records(metric):all_metrics.append({'horizon_weeks':horizon,'model':kind,**row})
            catalog.append({'modelo':kind,'horizonteSemanas':horizon,'dataAlvo':context['dataAlvo'],
                'previsao':str((directory/'previsao.json').relative_to(results)),
                'metricas':str((directory/'metricas.json').relative_to(results)),
                'explicabilidade':str((directory/'explicabilidade.json').relative_to(results)),
                'conclusao':str((directory/'conclusao.json').relative_to(results)),
                'resultadoCompleto':str((directory/'resultado_completo.json').relative_to(results))})
            print('Concluído',title,'acurácia histórica:',round(forecast['desempenhoHistorico']['acuracia'],4),flush=True)
    summary=pd.DataFrame(all_metrics)
    table(results/'comparacao/metricas_todos_modelos',summary)
    write_json(results/'catalogo.json',{'schemaVersion':'1.0.0','versao':'v1.0.0','resultados':catalog})
    fig,axes=plt.subplots(2,3,figsize=(15,9))
    test=summary[summary.split=='teste']
    for ax,(metric,label) in zip(axes.flat,METRICS.items()):
        for kind,name in MODELS.items():
            frame=test[test.model==kind].sort_values('horizon_weeks')
            ax.plot(frame.horizon_weeks,frame[metric],marker='o',color=COLORS[kind],label=name)
        ax.set(title=label,xlabel='Horizonte (semanas)',ylabel='Escore (0–1)',xticks=HORIZONS,ylim=(0,1.03));ax.legend(fontsize=8)
    fig.suptitle('V1 — avaliação histórica retrospectiva dos ensembles',fontsize=15)
    figure(results/'comparacao/visao_geral',fig)
    report='# V1 — relatório técnico\n\n'
    report+='Entradas sem ENSO, escolhidas pelo conjunto de resultados anteriores. Três famílias e horizontes de 4, 8, 12 e 16 semanas.\n\n'
    report+='Cada saída é a média de cinco sementes fixas; não se escolhe uma semente pelo teste. RF selecionado por F1, redes por perda BCE de validação. Limiar fixo 0,5.\n\n'
    report+='O alvo compara os casos da semana t+h à média das quatro semanas disponíveis antes de t, e não às quatro semanas imediatamente anteriores ao alvo. O critério é crescimento de casos, não confirmação epidemiológica de surto.\n\n'
    report+='As fronteiras são fixas, com remoção de amostras que cruzariam as datas de desfecho entre partições; scaler ajustado somente nas janelas do treino. O número de semanas avaliadas varia entre horizontes.\n\n'
    report+='O teste histórico já foi examinado em experimentos anteriores. As métricas são retrospectivas e exploratórias, não avaliação independente. As cinco sementes não substituem validação temporal externa. Não há refit após a avaliação: o ensemble da previsão é o mesmo ensemble avaliado historicamente.\n\n'
    report+='A última semana da base é a referência automática da previsão. Com a hipótese de disponibilidade de uma semana, as entradas e a média de referência terminam na semana anterior. Atualizar a base atualiza essas datas, sem mudar artificialmente seu calendário.\n\n'
    report+='O acerto histórico não é a probabilidade individual de acerto. Escores do modelo não foram calibrados. Dados podem sofrer atraso ou revisão; particularidades locais e mudanças de transmissão podem reduzir desempenho futuro.\n\n'
    report+='SHAP e Captum explicam a média das saídas dos cinco modelos (0–1). IG usa zero padronizado, a média do treino. Atribuições não demonstram causalidade. Gini é média das importâncias de cada floresta, com DP entre sementes.\n\n'
    report+='## Métricas do teste histórico\n\n'+test.to_csv(index=False)
    (results/'relatorio_tecnico.md').write_text(report,encoding='utf-8')
    table(results/'manifesto',pd.DataFrame([{'path':str(p.relative_to(results)),'bytes':p.stat().st_size}
        for p in sorted(results.rglob('*')) if p.is_file() and p.stem!='manifesto']))
    return summary


if __name__=='__main__':
    run_study(Path(__file__).resolve().parent.parent)
