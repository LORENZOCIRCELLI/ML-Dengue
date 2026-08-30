import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import DashboardScreen from '../screens/DashboardScreen';
import PredictionsScreen from '../screens/PredictionsScreen';
import ModelsScreen from '../screens/ModelsScreen';
import TrendsScreen from '../screens/TrendsScreen';
import NewsScreen from '../screens/NewsScreen';
import SettingsScreen from '../screens/SettingsScreen';
import { colors } from '../theme/colors';

export type RootTabParamList = {
  Dashboard: undefined;
  Predictions: undefined;
  Models: undefined;
  Trends: undefined;
  News: undefined;
  Settings: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();

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
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.muted,
          tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
          tabBarLabel: LABELS[route.name as keyof RootTabParamList],
          tabBarIcon: ({ color, size }) => (
            <Ionicons name={ICONS[route.name as keyof RootTabParamList]} color={color} size={size} />
          ),
        })}
      >
        <Tab.Screen name="Dashboard" component={DashboardScreen} />
        <Tab.Screen name="Predictions" component={PredictionsScreen} />
        <Tab.Screen name="Models" component={ModelsScreen} />
        <Tab.Screen name="Trends" component={TrendsScreen} />
        <Tab.Screen name="News" component={NewsScreen} />
        <Tab.Screen name="Settings" component={SettingsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
