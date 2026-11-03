import { useCallback, useEffect, useState } from 'react';
import {
  Image,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { getArbovirusNews, NewsArticle } from '../services/news';
import { cardShadow, colors, radii, spacing, typography } from '../theme/colors';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import ScreenHeader from '../components/ScreenHeader';
import { screenContent } from '../theme/layout';

export default function NewsScreen() {
  const [articles, setArticles] = useState<NewsArticle[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async () => {
    setError(null);
    try {
      setArticles(await getArbovirusNews());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro inesperado.');
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!articles) return <LoadingState label="Buscando notícias brasileiras..." />;
  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={async () => {
            setRefreshing(true);
            await load();
            setRefreshing(false);
          }}
        />
      }
    >
      <ScreenHeader
        title="Fique por dentro."
        subtitle="Notícias sobre arboviroses no Brasil."
        icon="newspaper-outline"
      />
      {articles.length === 0 && (
        <EmptyState
          title="Novidades a caminho."
          message="Nenhuma notícia encontrada agora. Puxe para atualizar."
        />
      )}
      {articles.map((article) => (
        <Pressable
          key={article.url}
          style={styles.card}
          onPress={() => Linking.openURL(article.url)}
        >
          {article.image ? (
            <Image source={{ uri: article.image }} style={styles.image} />
          ) : null}
          <View style={styles.body}>
            <Text style={styles.source}>
              {article.source} ·{' '}
              {new Date(article.publishedAt).toLocaleDateString('pt-BR')}
            </Text>
            <Text style={styles.headline}>{article.title}</Text>
            {!!article.description && (
              <Text style={styles.description} numberOfLines={3}>
                {article.description}
              </Text>
            )}
            <Text style={styles.link}>Abrir notícia →</Text>
          </View>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: screenContent,
  card: {
    ...cardShadow,
    backgroundColor: colors.surfaceSoft,
    borderWidth: 0,
    borderRadius: radii.lg,
    overflow: 'hidden',
    marginBottom: spacing.lg,
  },
  image: {
    width: '100%',
    height: 230,
    backgroundColor: colors.border,
  },
  body: {
    padding: spacing.lg,
  },
  source: {
    ...typography.caption,
    color: colors.primary,
    fontWeight: '700',
  },
  headline: {
    ...typography.h3,
    fontSize: 18,
    lineHeight: 24,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  description: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  link: {
    ...typography.body,
    color: colors.primary,
    fontWeight: '600',
    marginTop: spacing.sm,
  },
  empty: {
    ...typography.body,
    color: colors.muted,
    textAlign: 'center',
    marginTop: spacing.xl,
  },
});
