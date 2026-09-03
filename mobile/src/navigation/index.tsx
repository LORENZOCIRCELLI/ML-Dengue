import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { StyleSheet } from 'react-native';
import DashboardScreen from '../screens/DashboardScreen';
import PredictionsScreen from '../screens/PredictionsScreen';
import ModelsScreen from '../screens/ModelsScreen';
import NewsScreen from '../screens/NewsScreen';
import SettingsScreen from '../screens/SettingsScreen';
import { colors, spacing } from '../theme/colors';

export type RootTabParamList = {
  Dashboard: undefined;
  Predictions: undefined;
  Models: undefined;
  Trends: undefined;
  News: undefined;
  Settings: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();

function withSafeArea(Component: React.ComponentType) {
  return function SafeAreaScreen() {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
        <Component />
      </SafeAreaView>
    );
  };
}

const SafeDashboard = withSafeArea(DashboardScreen);
const SafePredictions = withSafeArea(PredictionsScreen);
const SafeModels = withSafeArea(ModelsScreen);
const SafeNews = withSafeArea(NewsScreen);
const SafeSettings = withSafeArea(SettingsScreen);

const ICONS: Record<keyof RootTabParamList, keyof typeof Ionicons.glyphMap> = {
  Dashboard: 'home',
  Predictions: 'analytics',
  Models: 'layers',
  Trends: 'trending-up',
  News: 'newspaper',
  Settings: 'settings',
};

const LABELS: Record<keyof RootTabParamList, string> = {
  Dashboard: 'Painel',
  Predictions: 'Previsões',
  Models: 'Modelos',
  Trends: 'Tendências',
  News: 'Notícias',
  Settings: 'Ajustes',
};

// Five top-level, always-visible tabs (Nielsen #4 — consistency & standards;
// #7 — flexibility: managers jump straight to what they need without
// digging through menus).
export default function RootNavigation() {
  const insets = useSafeAreaInsets();

  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.muted,
          tabBarHideOnKeyboard: true,
          tabBarLabelStyle: { fontSize: 10, fontWeight: '600', marginBottom: 4 },
          tabBarIconStyle: { marginTop: 5 },
          tabBarStyle: {
            backgroundColor: colors.surface,
            borderTopColor: colors.border,
            borderTopWidth: StyleSheet.hairlineWidth,
            height: 62 + insets.bottom,
            paddingTop: 3,
            paddingBottom: Math.max(insets.bottom, 6),
          },
          tabBarLabel: LABELS[route.name as keyof RootTabParamList],
          tabBarIcon: ({ color, size }) => (
            <Ionicons name={ICONS[route.name as keyof RootTabParamList]} color={color} size={size} />
          ),
        })}
      >
        <Tab.Screen name="Dashboard" component={SafeDashboard} />
        <Tab.Screen name="Predictions" component={SafePredictions} />
        <Tab.Screen name="Models" component={SafeModels} />
        <Tab.Screen name="News" component={SafeNews} />
        <Tab.Screen name="Settings" component={SafeSettings} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background, paddingTop: spacing.sm },
});
