"""Verificação independente das saídas V1, sem retreinar modelos."""
from pathlib import Path
import importlib.util
import json

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score, average_precision_score, confusion_matrix


def validate(project_root):
    root=Path(project_root).resolve();results=root/'v1/results'
    spec=importlib.util.spec_from_file_location('dengue_v1',root/'v1/estudo.py')
    api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
    torch.set_num_threads(1)
    df,features,_=api.load_data(root)
    available=features.shift(1)
    catalog=json.loads((results/'catalogo.json').read_text())['resultados']
    assert len(catalog)==12 and {(r['modelo'],r['horizonteSemanas']) for r in catalog}=={
        (m,h) for m in api.MODELS for h in api.HORIZONS}
    for h in api.HORIZONS:
        hd=results/'horizontes'/f'{h:02d}_semanas'
        samples=pd.read_csv(hd/'data/particoes.csv',parse_dates=['data_emissao','data_alvo'])
        assert samples.sample_id.is_unique
        assert samples.loc[samples.split=='treino','data_alvo'].max()<samples.loc[samples.split=='validacao','data_emissao'].min()
        assert samples.loc[samples.split=='validacao','data_alvo'].max()<samples.loc[samples.split=='teste','data_emissao'].min()
        for row in samples.itertuples():
            i=row.sample_id
            assert row.data_emissao==df.dt_pri_sem.iloc[i] and row.data_alvo==df.dt_pri_sem.iloc[i+h]
            baseline=df['n dengue'].iloc[i-4:i].mean()
            assert np.isclose(row.media_referencia,baseline)
            assert row.casos_futuros==df['n dengue'].iloc[i+h]
            assert row.target==int(row.casos_futuros>=1.5*baseline)
        scaler=joblib.load(hd/'scaler.joblib')
        train_samples=samples[samples.split=='treino']
        raw=np.stack([available.iloc[i-11:i+1].to_numpy() for i in train_samples.sample_id])
        np.testing.assert_allclose(scaler.mean_,raw.reshape(-1,6).mean(axis=0),atol=1e-10)
        latest=scaler.transform(available.iloc[-12:].to_numpy()).reshape(1,72).astype(np.float32)
        for kind in api.MODELS:
            directory=hd/kind
            models=[]
            history=pd.read_csv(directory/'metrics/historico_treinamento.csv')
            for seed in api.SEEDS:
                hist=history[(history.seed==seed)&(history.split=='validacao')]
                if kind=='random_forest':
                    model=joblib.load(directory/f'artifacts/seed_{seed}.joblib')
                    assert model.n_estimators==hist.loc[hist.f1.idxmax(),'step']
                else:
                    ck=torch.load(directory/f'artifacts/seed_{seed}.pt',weights_only=True)
                    assert ck['selected_epoch']==hist.loc[hist.loss.idxmin(),'step']
                    model=api.SequenceClassifier(kind);model.load_state_dict(ck['state_dict']);model.eval()
                models.append(model)
            metric=pd.read_csv(directory/'metrics/metricas_ensemble.csv').set_index('split')
            for split in api.SPLITS:
                data=pd.read_csv(hd/f'data/{split}_padronizado.csv')
                X=data.drop(columns=['sample_id','target']).to_numpy(dtype=np.float32)
                pred=pd.read_csv(directory/f'data/previsoes_{split}.csv')
                p=api.predict(kind,models,X).mean(axis=0)
                np.testing.assert_allclose(pred.escore_aumento,p,atol=1e-7,rtol=1e-6)
                assert pred.sample_id.tolist()==data.sample_id.tolist()
                assert pred.target.tolist()==data.target.tolist()
                target=pred.target.to_numpy();decision=p>=.5
                expected={'accuracy':accuracy_score(target,decision),'f1':f1_score(target,decision,zero_division=0),
                    'precision':precision_score(target,decision,zero_division=0),'recall':recall_score(target,decision,zero_division=0),
                    'roc_auc':roc_auc_score(target,p),'pr_auc':average_precision_score(target,p)}
                assert all(np.isclose(metric.loc[split,k],v) for k,v in expected.items())
            forecast=json.loads((directory/'previsao.json').read_text())
            actual=api.predict(kind,models,latest).mean()
            assert np.isclose(forecast['escoreAumentoNaoCalibrado'],actual)
            assert forecast['aumentoCasosPrevisto']==bool(actual>=.5)
            assert pd.Timestamp(forecast['dataAlvo'])==df.dt_pri_sem.iloc[-1]+pd.Timedelta(weeks=h)
            test=pd.read_csv(directory/'data/previsoes_teste.csv')
            historic=forecast['desempenhoHistorico']
            assert historic['semanasAvaliadas']==len(test)
            assert np.isclose(historic['acuracia'],accuracy_score(test.target,test.prediction))
            assert np.isclose(historic['acuraciaPercentual'],100*historic['acuracia'])
            assert (f"{historic['acuraciaPercentual']:.1f}".replace('.',',')+'%') in forecast['textoConclusao']
            assert f"{len(test)} semanas" in forecast['textoConclusao']
            assert historic['matrizConfusao']['valores']==confusion_matrix(test.target,test.prediction,labels=[0,1]).tolist()
            conclusion=json.loads((directory/'conclusao.json').read_text())
            assert conclusion['texto']==forecast['textoConclusao'] and conclusion['experimental']
            exp=json.loads((directory/'explicabilidade.json').read_text())
            for method,info in exp['metodos'].items():
                attrs=pd.DataFrame(info['atribuicoesTeste'])
                values=attrs.drop(columns='sample_id').to_numpy()
                assert attrs.sample_id.tolist()==test.sample_id.tolist() and values.shape==(len(test),72)
                assert np.isfinite(values).all()
                local=pd.DataFrame(info['previsao'])
                np.testing.assert_allclose(local.standardized_input,latest[0],rtol=1e-6,atol=1e-7)
                if method in ['shap','integrated_gradients']:
                    baseline=exp['diagnosticos'][method]['valorBase']
                    tolerance=1e-5 if method=='shap' else .01
                    np.testing.assert_allclose(baseline+values.sum(axis=1),test.escore_aumento,atol=tolerance,rtol=0)
                    assert abs(baseline+local.attribution.sum()-actual)<tolerance
            combined=json.loads((directory/'resultado_completo.json').read_text())
            assert combined['previsao']==forecast and combined['explicabilidade']==exp
            print(f'OK: {h} semanas / {kind}: dados, modelo, métricas, projeção e atribuições.',flush=True)
    for path in results.rglob('*.json'):
        json.loads(path.read_text(),parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        csv=path.with_suffix('.csv')
        if csv.exists() and path.stem!='manifesto':
            original=pd.read_csv(csv);data=pd.DataFrame(json.loads(path.read_text()))
            # Datas ISO podem receber formatação de hora diferente entre CSV e JSON.
            for col in original.columns:
                if pd.api.types.is_string_dtype(original[col]) and len(original) and original[col].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}').all():
                    original[col]=pd.to_datetime(original[col]);data[col]=pd.to_datetime(data[col])
            pd.testing.assert_frame_equal(original,data,check_dtype=False,check_exact=False,rtol=1e-6,atol=1e-7)
    manifest=pd.read_csv(results/'manifesto.csv')
    assert all((results/row.path).stat().st_size==row.bytes for row in manifest.itertuples())
    print('V1: 12 combinações verificadas; CSV/JSON e inventário válidos.',flush=True)


if __name__=='__main__':
    validate(Path(__file__).resolve().parent.parent)
