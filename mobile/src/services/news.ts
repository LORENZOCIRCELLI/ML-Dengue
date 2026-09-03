export interface NewsArticle { title: string; description: string; url: string; image?: string; publishedAt: string; source: string; }
interface GNewsResponse { articles?: Array<{ title: string; description?: string; url: string; image?: string; publishedAt: string; source?: { name?: string } }>; errors?: string[]; }
const QUERY = 'dengue OR chikungunya OR zika OR arbovirose OR "febre amarela"';
export async function getArbovirusNews(): Promise<NewsArticle[]> {
  const url = `https://gnews.io/api/v4/search?q=${encodeURIComponent(QUERY)}&lang=pt&country=br&max=10&sortby=publishedAt&apikey=e0cac16c9104741e604dff737a6b5bbd`;
  const response = await fetch(url);
  const body = await response.json() as GNewsResponse;
  if (!response.ok) throw new Error(body.errors?.[0] ?? 'Não foi possível carregar as notícias.');
  return (body.articles ?? []).map(article => ({ title: article.title, description: article.description ?? '', url: article.url, image: article.image, publishedAt: article.publishedAt, source: article.source?.name ?? 'Notícia brasileira' }));
}
