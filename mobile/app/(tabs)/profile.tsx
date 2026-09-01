import { View, Text, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../../store/useAuthStore';
import * as SecureStore from 'expo-secure-store';
import { useRouter } from 'expo-router';

export default function ProfileTab() {
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = async () => {
    await SecureStore.deleteItemAsync('authToken');
    logout();
    router.replace('/(auth)/login');
  };

  return (
    <SafeAreaView className="flex-1 bg-brand-slate items-center py-10">
      <View className="w-24 h-24 rounded-full bg-brand-blue items-center justify-center mb-4">
        <Text className="text-white text-3xl font-bold">
          {user?.first_name?.[0]}{user?.last_name?.[0]}
        </Text>
      </View>
      <Text className="text-white text-2xl font-bold">{user?.first_name} {user?.last_name}</Text>
      <Text className="text-gray-400 mt-1">{user?.email}</Text>

      <TouchableOpacity 
        className="mt-10 bg-red-500/20 px-8 py-3 rounded-full border border-red-500/50"
        onPress={handleLogout}
      >
        <Text className="text-red-400 font-bold text-lg">Log Out</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}
