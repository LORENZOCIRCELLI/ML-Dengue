import { DATA_SOURCE } from '../config/api.config';
import { mockProvider } from './providers/mockProvider';
import { awsProvider, ApiError } from './providers/awsProvider';

// ---------------------------------------------------------------------------
// Ponto único de acesso a dados para toda a UI. Nenhuma tela ou componente
// deve importar mockProvider/awsProvider diretamente — sempre `api` daqui.
//
// A troca entre mock e AWS é 100% controlada por DATA_SOURCE em
// src/config/api.config.ts (ou pela env var EXPO_PUBLIC_DATA_SOURCE).
// As duas implementações têm a mesma assinatura, então trocar a fonte de
// dados nunca exige mudança em screens/components.
// ---------------------------------------------------------------------------

export const api = DATA_SOURCE === 'aws' ? awsProvider : mockProvider;

export { ApiError };
