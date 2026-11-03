const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

require.extensions['.ts'] = (module, filename) => {
  const source = fs.readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
    fileName: filename,
  });
  module._compile(compiled.outputText, filename);
};

const { results } = require('../src/services/results.ts');
const { RESULTS_CONFIG } = require('../src/config/results.config.ts');
const { displayDate } = require('../src/utils/results.ts');
const originalFetch = global.fetch;
const originalUrl = RESULTS_CONFIG.baseUrl;
const exported = path.resolve(__dirname, '../../export');

function localJson(relative) {
  return JSON.parse(fs.readFileSync(path.join(exported, relative), 'utf8'));
}

test.afterEach(() => {
  RESULTS_CONFIG.baseUrl = originalUrl;
  global.fetch = originalFetch;
});

test('lê os 12 resultados reais e mantém métricas e conclusões coerentes', async () => {
  RESULTS_CONFIG.baseUrl = undefined;
  global.fetch = () => {
    throw new Error('A leitura local não pode acessar a rede.');
  };
  const catalog = await results.getCatalog();
  assert.equal(catalog.resultados.length, 12);
  for (const entry of catalog.resultados) {
    const forecast = await results.getForecast(entry);
    const metrics = await results.getMetrics(entry);
    const explanation = await results.getExplanation(entry);
    const conclusion = await results.getConclusion(entry);
    const historical = metrics.metricas.find((row) => row.split === 'teste');
    assert.equal(forecast.modelo, entry.modelo);
    assert.equal(forecast.horizonteSemanas, entry.horizonteSemanas);
    assert.equal(historical.n_samples, forecast.desempenhoHistorico.semanasAvaliadas);
    assert.ok(
      Math.abs(historical.accuracy - forecast.desempenhoHistorico.acuracia) < 1e-12,
    );
    assert.equal(conclusion.texto, forecast.textoConclusao);
    assert.deepEqual(
      Object.keys(explanation.metodos).sort(),
      entry.modelo === 'random_forest' ? ['shap'] : ['integrated_gradients', 'saliency'],
    );
    for (const method of Object.values(explanation.metodos)) {
      assert.equal(method.importanciaPorVariavel.length, 6);
      assert.equal(method.previsao.length, 72);
    }
  }
  const dataset = await results.getDataset();
  assert.equal(dataset.length, 784);
  assert.equal(dataset.at(-1).casos_dengue, 200);
});

test('consulta a URL-base com os mesmos caminhos do catálogo', async () => {
  RESULTS_CONFIG.baseUrl = 'https://example.test/export';
  const requested = [];
  global.fetch = async (url) => {
    assert.ok(url.startsWith(RESULTS_CONFIG.baseUrl + '/'));
    const relative = url.slice(RESULTS_CONFIG.baseUrl.length + 1);
    requested.push(relative);
    return { ok: true, json: async () => localJson(relative) };
  };
  const catalog = await results.getCatalog();
  for (const entry of catalog.resultados) {
    await results.getForecast(entry);
    await results.getMetrics(entry);
    await results.getExplanation(entry);
    await results.getConclusion(entry);
  }
  await results.getDataset();
  assert.equal(requested.length, 50);
  assert.ok(
    !requested.some((value) => value.includes('v1/results') || value.includes('outputs')),
  );
});

test('falha remota é exibida sem substituir os dados por mocks ou cópias locais', async () => {
  RESULTS_CONFIG.baseUrl = 'https://example.test/export';
  global.fetch = async () => ({ ok: false, status: 503 });
  await assert.rejects(results.getCatalog(), /HTTP 503/);
});

test('rejeita previsão de outro modelo ou horizonte', async () => {
  RESULTS_CONFIG.baseUrl = 'https://example.test/export';
  const catalog = localJson('catalogo.json');
  const first = catalog.resultados[0];
  const second = catalog.resultados[1];
  global.fetch = async () => ({ ok: true, json: async () => localJson(second.previsao) });
  await assert.rejects(results.getForecast(first), /não corresponde/);
});

test('rejeita versões incompatíveis e caminhos externos no catálogo', async () => {
  RESULTS_CONFIG.baseUrl = 'https://example.test/export';
  let invalid = { ...localJson('catalogo.json'), schemaVersion: '999' };
  global.fetch = async () => ({ ok: true, json: async () => invalid });
  await assert.rejects(results.getCatalog(), /incompatível/);
  invalid = structuredClone(localJson('catalogo.json'));
  invalid.resultados[0].previsao = '../outside.json';
  await assert.rejects(results.getCatalog(), /caminho/);
});

test('datas de semanas não mudam com o fuso horário', () => {
  assert.equal(displayDate('2026-01-25'), '25/01/2026');
  assert.equal(displayDate('2025-12-28T00:00:00.000'), '28/12/2025');
});

test('rejeita arquivos incompletos antes de renderizar métricas ou explicabilidade', async () => {
  RESULTS_CONFIG.baseUrl = 'https://example.test/export';
  const entry = localJson('catalogo.json').resultados[0];
  let invalid = localJson(entry.metricas);
  invalid.metricas[0].accuracy = '88%';
  global.fetch = async () => ({ ok: true, json: async () => invalid });
  await assert.rejects(results.getMetrics(entry), /JSON de métricas/);
  invalid = localJson(entry.explicabilidade);
  delete invalid.metodos.shap.previsao;
  await assert.rejects(results.getExplanation(entry), /explicabilidade/);
  invalid = localJson(entry.previsao);
  delete invalid.desempenhoHistorico.acuracia;
  await assert.rejects(results.getForecast(entry), /previsão/);
});
