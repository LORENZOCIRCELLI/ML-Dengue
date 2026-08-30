export interface NewsArticle { title: string; description: string; url: string; image?: string; publishedAt: string; source: string; }
interface GNewsResponse { articles?: Array<{ title: string; description?: string; url: string; image?: string; publishedAt: string; source?: { name?: string } }>; errors?: string[]; }
const QUERY = 'dengue OR chikungunya OR zika OR arbovirose OR "febre amarela"';
export async function getArbovirusNews(): Promise<NewsArticle[]> {
  const key = process.env.EXPO_PUBLIC_GNEWS_API_KEY;
  if (!key) throw new Error('Configure EXPO_PUBLIC_GNEWS_API_KEY para carregar as notícias.');
  const params = new URLSearchParams({ q: QUERY, lang: 'pt', country: 'br', max: '10', sortby: 'publishedAt', apikey: key });
  const response = await fetch(`https://gnews.io/api/v4/search?${params}`);
  const body = await response.json() as GNewsResponse;
  if (!response.ok) throw new Error(body.errors?.[0] ?? 'Não foi possível carregar as notícias.');
  return (body.articles ?? []).map(article => ({ title: article.title, description: article.description ?? '', url: article.url, image: article.image, publishedAt: article.publishedAt, source: article.source?.name ?? 'Notícia brasileira' }));
}
