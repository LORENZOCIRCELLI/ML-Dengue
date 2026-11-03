"""Experimento fixo com Random Forest e dois resumos de ONI; validação somente."""
from pathlib import Path
import copy
import hashlib
import json

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (f1_score, precision_score, recall_score, accuracy_score,
                             roc_auc_score, average_precision_score, log_loss)

SEEDS = [42, 123, 2025, 7, 99]
TREE_COUNTS = [25, 50, 100, 200]
METRICS = ['f1', 'pr_auc', 'precision', 'recall', 'roc_auc', 'accuracy']
LABELS = {'f1': 'F1', 'pr_auc': 'PR-AUC (Average Precision)', 'precision': 'Precisão',
          'recall': 'Recall', 'roc_auc': 'ROC-AUC', 'accuracy': 'Acurácia'}
VARIANTS = {'sem_ENSO': 'Sem ENSO', 'ONI_recente': 'ONI recente', 'ONI_media12': 'ONI — média de 12 semanas'}
COLORS = {'sem_ENSO': '#2563EB', 'ONI_recente': '#D97706', 'ONI_media12': '#059669'}


def records(frame):
    return json.loads(frame.replace([np.inf, -np.inf], np.nan).to_json(
        orient='records', force_ascii=False, double_precision=15))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def scores(y, prob):
    prediction = (prob >= .5).astype(int)
    return {'f1': f1_score(y, prediction, zero_division=0),
        'pr_auc': average_precision_score(y, prob),
        'precision': precision_score(y, prediction, zero_division=0),
        'recall': recall_score(y, prediction, zero_division=0),
        'roc_auc': roc_auc_score(y, prob), 'accuracy': accuracy_score(y, prediction),
        'n': len(y), 'positive': int(np.sum(y)), 'predicted_positive': int(prediction.sum())}


def run_experiment(project_root):
    root = Path(project_root).resolve()
    reference = root/'experimento_sem_ONI/results'
    results = root/'experimento_ONI_resumido/results'
    dirs = {name: results/name for name in ['data','metrics','figures','artifacts','json']}
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    meta = json.loads((reference/'random_forest/metadata.json').read_text())
    frames, base, target, ids, hashes = {}, {}, {}, {}, {}
    for split in ['treino','validacao']:
        path = reference/'random_forest/data'/f'{split}_padronizado.csv'
        hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest()
        frames[split] = pd.read_csv(path)
        base[split] = frames[split][meta['features']].to_numpy(dtype=np.float32)
        target[split] = frames[split].target.to_numpy(dtype=np.int64)
        ids[split] = frames[split].sample_id.to_numpy(dtype=int)
        assert set(target[split]) == {0,1}
    samples = pd.read_csv(reference/'data/amostras_e_particoes.csv',
        parse_dates=['data_emissao','data_alvo'])
    samples = samples[samples.split.isin(['treino','validacao'])].copy()
    assert samples.loc[samples.split.eq('treino'),'data_alvo'].max() < samples.loc[samples.split.eq('validacao'),'data_emissao'].min()
    samples.to_csv(dirs['data']/'amostras_e_particoes.csv', index=False)
    raw = pd.read_csv(reference/'data/dataset_origem.csv', parse_dates=['dt_pri_sem'])
    raw = raw[raw.dt_pri_sem <= pd.Timestamp(meta['validation_end'])].copy()
    # Definições fixadas antes da execução: nenhum outro atraso ou janela é testado.
    recent = raw.ONI.shift(4)
    mean12 = recent.rolling(12, min_periods=12).mean()
    available = pd.DataFrame({'sample_id': raw.index, 'data_emissao': raw.dt_pri_sem,
        'ONI_recente': recent, 'ONI_media12': mean12})
    available.to_csv(dirs['data']/'resumos_ONI_disponiveis.csv', index=False)
    configuration = {'model': 'random_forest', 'variants': VARIANTS, 'seeds': SEEDS,
        'horizon_weeks': 4, 'target': meta['target_definition'], 'threshold': .5,
        'selection': 'maior F1 de validação; primeiro em empate',
        'base_features': meta['features'], 'base_input_sha256': hashes,
        'oni_recent': 'ONI(t−4)', 'oni_mean12': 'média ONI(t−15 ... t−4)',
        'oni_units_original': '°C (anomalia)', 'added_features_per_variant': {'sem_ENSO':0,'ONI_recente':1,'ONI_media12':1},
        'preprocessing': 'base já padronizada no treino; cada resumo ONI padronizado somente no treino',
        'trees': TREE_COUNTS, 'max_depth': 6, 'min_samples_leaf': 2, 'class_weight': 'balanced',
        'test_evaluated': False, 'window_selected_by_results': False,
        'primary_metrics': ['f1','pr_auc'], 'pr_auc_definition': 'sklearn.average_precision_score',
        'font': 'DejaVu Sans', 'colors': COLORS}
    write_json(results/'metadata.json', configuration)
    metric_rows, prediction_rows, history_rows = [], [], []
    for variant in VARIANTS:
        arrays = {split: a.copy() for split, a in base.items()}
        names = list(meta['features'])
        if variant != 'sem_ENSO':
            scalar = {split: available.loc[ids[split],variant].to_numpy().reshape(-1,1)
                      for split in ids}
            assert all(np.isfinite(a).all() for a in scalar.values())
            scaler = StandardScaler().fit(scalar['treino'])
            arrays = {split: np.column_stack([base[split],scaler.transform(scalar[split])]).astype(np.float32)
                      for split in base}
            names.append(variant)
            joblib.dump(scaler, dirs['artifacts']/f'{variant}_scaler.joblib')
        for split in arrays:
            frame = pd.DataFrame(arrays[split],columns=names,index=ids[split])
            frame.index.name='sample_id'
            frame['target']=target[split]
            frame.to_csv(dirs['data']/f'{variant}_{split}_padronizado.csv')
        for seed in SEEDS:
            best_score = -np.inf
            for trees in TREE_COUNTS:
                candidate = RandomForestClassifier(n_estimators=trees,max_depth=6,min_samples_leaf=2,
                    class_weight='balanced',random_state=seed,n_jobs=1)
                candidate.fit(arrays['treino'],target['treino'])
                for split in ['treino','validacao']:
                    prob=candidate.predict_proba(arrays[split])[:,1]
                    metric=scores(target[split],prob)
                    history_rows.append({'variant':variant,'seed':seed,'step':trees,'split':split,
                        'loss':log_loss(target[split],prob,labels=[0,1]),**metric})
                    if split=='validacao' and metric['f1']>best_score:
                        best_score=metric['f1'];selected_step=trees;model=copy.deepcopy(candidate)
            probability=model.predict_proba(arrays['validacao'])[:,1]
            metric_rows.append({'variant':variant,'seed':seed,'selected_trees':selected_step,
                **scores(target['validacao'],probability)})
            prediction_rows.extend({'variant':variant,'seed':seed,'sample_id':int(i),'target':int(y),
                'probability':float(p),'prediction':int(p>=.5)}
                for i,y,p in zip(ids['validacao'],target['validacao'],probability))
            joblib.dump(model,dirs['artifacts']/f'{variant}_seed_{seed}.joblib')
            print(variant,seed,'F1:',round(metric_rows[-1]['f1'],4),flush=True)
    metrics=pd.DataFrame(metric_rows)
    metrics.to_csv(dirs['metrics']/'metricas_validacao_por_semente.csv',index=False)
    pd.DataFrame(prediction_rows).to_csv(dirs['data']/'previsoes_validacao.csv',index=False)
    pd.DataFrame(history_rows).to_csv(dirs['metrics']/'historico_treinamento.csv',index=False)
    summary=pd.DataFrame([{'variant':variant,'metric':metric,'n_runs':len(group),
        'mean':group[metric].mean(),'std':group[metric].std(ddof=1),
        'min':group[metric].min(),'max':group[metric].max()}
        for variant,group in metrics.groupby('variant',sort=False) for metric in METRICS])
    summary.to_csv(dirs['metrics']/'resumo_validacao.csv',index=False)
    reference_metrics=metrics[metrics.variant=='sem_ENSO']
    pairs=[]
    for variant in ['ONI_recente','ONI_media12']:
        merged=reference_metrics.merge(metrics[metrics.variant==variant],on='seed',validate='one_to_one',suffixes=('_base','_oni'))
        for _,row in merged.iterrows():
            for metric in METRICS:
                pairs.append({'variant':variant,'seed':int(row.seed),'metric':metric,
                    'baseline':row[metric+'_base'],'with_oni':row[metric+'_oni'],
                    'delta':row[metric+'_oni']-row[metric+'_base']})
    pairs=pd.DataFrame(pairs)
    pairs.to_csv(dirs['metrics']/'diferencas_por_semente.csv',index=False)
    paired_summary=pairs.groupby(['variant','metric'],sort=False).agg(n_pairs=('delta','size'),
        mean_delta=('delta','mean'),std_delta=('delta','std'),
        positive_deltas=('delta',lambda v:int((v>1e-10).sum())),
        negative_deltas=('delta',lambda v:int((v < -1e-10).sum()))).reset_index()
    paired_summary.to_csv(dirs['metrics']/'resumo_diferencas.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'white',
        'axes.facecolor':'white','axes.grid':True,'grid.alpha':.2,
        'axes.spines.top':False,'axes.spines.right':False})
    graphs=[]
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,metric in zip(axes,['f1','pr_auc']):
        rows=summary[summary.metric==metric]
        bars=ax.bar(np.arange(3),rows['mean'],yerr=rows['std'],capsize=4,
                    color=[COLORS[v] for v in rows.variant])
        ax.bar_label(bars,fmt='%.3f',padding=8)
        ax.set(xticks=np.arange(3),xticklabels=['Sem ENSO','ONI recente','Média ONI — 12 semanas'],
               title=LABELS[metric],ylabel='Escore (0–1)',ylim=(0,1.05))
        ax.tick_params(axis='x',rotation=15)
        graphs.append({'id':f'oni_resumido/{metric}','titulo':LABELS[metric],'tipo':'barras',
            'eixoX':'Representação de ONI','eixoY':'Escore (0–1)',
            'barrasErro':'DP entre cinco sementes; não intervalo de confiança',
            'series':[{'id':r.variant,'cor':COLORS[r.variant],
                'pontos':[{'x':VARIANTS[r.variant],'y':r.mean,'erroY':r.std}]}
                for r in rows.itertuples(index=False)]})
    fig.suptitle('Random Forest — validação — ONI resumido',fontsize=15)
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(dirs['figures']/f'01_comparacao_ONI_resumido.{ext}',dpi=160,bbox_inches='tight')
    plt.show();plt.close(fig)
    report='# Random Forest — ONI resumido na validação\n\n'
    report+='Dois resumos predefinidos; nenhum outro atraso ou janela foi testado. Mesmos atributos de base, alvo, datas e cinco sementes.\n\n'
    report+='| Entrada | F1 média ± DP | PR-AUC (AP) média ± DP |\n|---|---:|---:|\n'
    for variant,label in VARIANTS.items():
        row=summary[summary.variant==variant].set_index('metric')
        report+=f'| {label} | {row.loc["f1","mean"]:.3f} ± {row.loc["f1","std"]:.3f} | {row.loc["pr_auc","mean"]:.3f} ± {row.loc["pr_auc","std"]:.3f} |\n'
    report+='\n## Comparação pareada com a referência sem ENSO\n\n'
    for row in paired_summary[paired_summary.metric.isin(['f1','pr_auc'])].itertuples():
        report+=f'- {VARIANTS[row.variant]}, {LABELS[row.metric]}: diferença média {row.mean_delta:+.3f}; melhorou em {row.positive_deltas} de 5 sementes.\n'
    report+=('\nOs resultados são exploratórios no período de validação já examinado. As cinco sementes '
        'medem variação de treinamento, não generalização temporal; DP não é intervalo de confiança. '
        'O teste não foi reavaliado. Ausência de ganho nestas configurações não prova ausência de '
        'associação entre ENSO e dengue.\n')
    (results/'relatorio.md').write_text(report,encoding='utf-8')
    tables={}
    for path in sorted(results.rglob('*.csv')):
        if 'json' in path.relative_to(results).parts or path.name=='manifest.csv':continue
        relative=path.relative_to(results).with_suffix('.json')
        data=records(pd.read_csv(path))
        write_json(dirs['json']/relative,data)
        tables[str(path.relative_to(results).with_suffix(''))]=data
    write_json(results/'app_resultados.json',{'schemaVersion':'1.0.0','configuracao':configuration,
        'resumo':records(summary),'comparacaoPareada':records(paired_summary),
        'tabelas':tables,'graficos':graphs,'evaluation_split':'validacao','test_evaluated':False})
    pd.DataFrame([{'path':str(p.relative_to(results)),'bytes':p.stat().st_size}
        for p in sorted(results.rglob('*')) if p.is_file() and p.name!='manifest.csv']).to_csv(results/'manifest.csv',index=False)
    return summary


if __name__=='__main__':
    run_experiment(Path(__file__).resolve().parent.parent)
