import { Redirect } from 'expo-router';
import { useAuthStore } from '../store/useAuthStore';

export default function Index() {
  const { token } = useAuthStore();

  if (!token) {
    return <Redirect href="/(auth)/login" />;
  }

  return <Redirect href="/(tabs)/dashboard" />;
}
