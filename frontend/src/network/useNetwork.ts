import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import type { NetworkData } from './model';

export function useNetworkData() {
  return useQuery({ queryKey: ['network-workspace'], queryFn: () => api<NetworkData>('/network/workspace') });
}
