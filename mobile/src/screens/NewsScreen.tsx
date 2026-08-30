import React, { useCallback, useEffect, useState } from 'react';
import { Image, Linking, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { getArbovirusNews, NewsArticle } from '../services/news';
import { colors, radii, spacing, typography } from '../theme/colors';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
export default function NewsScreen() {
  const [articles, setArticles] = useState<NewsArticle[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    setError(null);
    try { setArticles(await getArbovirusNews()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Erro inesperado.'); }
  }, []);
  useEffect(() => { load(); }, [load]);
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!articles) return <LoadingState label="Buscando notícias brasileiras..." />;
  return <ScrollView style={styles.screen} contentContainerStyle={styles.content}
    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
    <Text style={styles.title}>Notícias</Text><Text style={styles.subtitle}>Dengue, zika, chikungunya e outras arboviroses no Brasil.</Text>
    {articles.length === 0 && <Text style={styles.empty}>Nenhuma notícia encontrada agora.</Text>}
    {articles.map(article => <Pressable key={article.url} style={styles.card} onPress={() => Linking.openURL(article.url)}>
      {article.image ? <Image source={{ uri: article.image }} style={styles.image} /> : null}
      <View style={styles.body}><Text style={styles.source}>{article.source} · {new Date(article.publishedAt).toLocaleDateString('pt-BR')}</Text>
        <Text style={styles.headline}>{article.title}</Text>{!!article.description && <Text style={styles.description} numberOfLines={3}>{article.description}</Text>}
        <Text style={styles.link}>Abrir notícia →</Text></View>
    </Pressable>)}
  </ScrollView>;
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background }, content: { padding: spacing.md, paddingBottom: spacing.xl },
  title: { ...typography.h1, color: colors.textPrimary }, subtitle: { ...typography.body, color: colors.textSecondary, marginBottom: spacing.md },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, overflow: 'hidden', marginBottom: spacing.md },
  image: { width: '100%', height: 170, backgroundColor: colors.border }, body: { padding: spacing.md }, source: { ...typography.caption, color: colors.primary, fontWeight: '600' },
  headline: { ...typography.h3, color: colors.textPrimary, marginTop: spacing.xs }, description: { ...typography.body, color: colors.textSecondary, marginTop: spacing.sm },
  link: { ...typography.body, color: colors.primary, fontWeight: '600', marginTop: spacing.sm }, empty: { ...typography.body, color: colors.muted, textAlign: 'center', marginTop: spacing.xl },
});
