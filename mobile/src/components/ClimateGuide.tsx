import { useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radii, typography } from '../theme/colors';

const sections = [
  {
    title: 'Dengue e clima',
    text: 'A dengue é transmitida principalmente pela picada da fêmea do Aedes aegypti infectada. Temperatura e chuva influenciam as condições para o mosquito e a transmissão. Urbanização, saneamento e circulação dos vírus também importam.',
  },
  {
    title: 'El Niño: a fase quente',
    text: 'É o aquecimento das águas superficiais do Pacífico Equatorial acima da média, associado a mudanças na atmosfera. Pode alterar a chuva e a temperatura em diferentes regiões.',
  },
  {
    title: 'La Niña: a fase fria',
    text: 'É o resfriamento dessas águas abaixo da média. É a fase oposta ao El Niño. Há também períodos de neutralidade, sem as condições que caracterizam essas duas fases.',
  },
  {
    title: 'O que isso significa para a dengue?',
    text: 'Mudanças no clima podem favorecer a transmissão, mas o efeito depende da região e das condições locais. El Niño não significa automaticamente mais dengue, nem La Niña significa proteção. A presença de um fenômeno, sozinha, não confirma um surto.',
  },
];

const references = [
  {
    title: 'Ministério da Saúde · Dengue',
    url: 'https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dengue',
  },
  {
    title: 'Ministério da Saúde · El Niño e La Niña',
    url: 'https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/e/el-nino/el-nino/',
  },
];

export default function ClimateGuide() {
  const [expanded, setExpanded] = useState(false);
  const [linkError, setLinkError] = useState(false);

  async function openReference(url: string) {
    setLinkError(false);
    try {
      await Linking.openURL(url);
    } catch {
      setLinkError(true);
    }
  }

  return (
    <View style={styles.container}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Dengue e clima: saiba mais"
        accessibilityState={{ expanded }}
        onPress={() => setExpanded((value) => !value)}
        style={({ pressed }) => [styles.button, pressed && styles.pressed]}
      >
        <Ionicons name="partly-sunny-outline" size={24} color={colors.textPrimary} />
        <View style={styles.buttonCopy}>
          <Text style={styles.title}>Dengue e clima</Text>
          <Text style={styles.caption}>Entenda o El Niño e a La Niña.</Text>
        </View>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={20}
          color={colors.textPrimary}
        />
      </Pressable>
      {expanded && (
        <View style={styles.content}>
          {sections.map((section) => (
            <View key={section.title} style={styles.section}>
              <Text accessibilityRole="header" style={styles.title}>
                {section.title}
              </Text>
              <Text style={styles.body}>{section.text}</Text>
            </View>
          ))}
          <Text accessibilityRole="header" style={styles.title}>
            Referências
          </Text>
          <Text style={styles.caption}>
            Conteúdo resumido de uma única instituição: Ministério da Saúde.
          </Text>
          {references.map((reference) => (
            <Pressable
              key={reference.url}
              accessibilityRole="link"
              accessibilityLabel={reference.title}
              onPress={() => openReference(reference.url)}
              style={styles.reference}
            >
              <Text style={styles.link}>{reference.title}</Text>
              <Text style={styles.url}>{reference.url}</Text>
            </Pressable>
          ))}
          {linkError && (
            <Text accessibilityRole="alert" style={styles.caption}>
              Não foi possível abrir o link. Você pode consultar o endereço acima no
              navegador.
            </Text>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.lavender,
    borderRadius: radii.md,
    marginBottom: 24,
    overflow: 'hidden',
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 20,
    minHeight: 76,
  },
  pressed: { opacity: 0.7 },
  buttonCopy: { flex: 1 },
  title: { ...typography.h3, color: colors.textPrimary },
  caption: { ...typography.caption, color: colors.textSecondary, marginTop: 6 },
  content: { paddingHorizontal: 22, paddingBottom: 24 },
  section: { marginBottom: 24 },
  body: { ...typography.body, color: colors.textPrimary, marginTop: 10 },
  reference: { paddingVertical: 14 },
  link: {
    ...typography.body,
    fontWeight: '600',
    textDecorationLine: 'underline',
    color: colors.textPrimary,
  },
  url: { ...typography.caption, color: colors.textSecondary, marginTop: 6 },
});
