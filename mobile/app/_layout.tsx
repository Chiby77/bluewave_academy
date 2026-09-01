import { Stack } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { useAuthStore } from '../store/useAuthStore';
import { useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import '../global.css'; // NativeWind CSS

const queryClient = new QueryClient();

export default function RootLayout() {
  const { setAuth } = useAuthStore();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    async function loadToken() {
      try {
        const token = await SecureStore.getItemAsync('authToken');
        if (token) {
          // We can optionally fetch the profile here to restore the user state,
          // for now, we just restore the token.
          setAuth(token, null);
        }
      } catch (e) {
        console.warn('Error loading auth token', e);
      } finally {
        setIsReady(true);
      }
    }
    loadToken();
  }, []);

  if (!isReady) {
    return null; // Or a splash screen
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
      </Stack>
      <StatusBar style="light" />
    </QueryClientProvider>
  );
}
