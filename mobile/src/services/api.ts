import { DATA_SOURCE } from '../config/api.config';
import { mockProvider } from './providers/mockProvider';
import { awsProvider, ApiError } from './providers/awsProvider';

export const api = DATA_SOURCE === 'aws' ? awsProvider : mockProvider;

export { ApiError };
