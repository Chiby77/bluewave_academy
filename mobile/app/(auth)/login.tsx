import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import { useAuthStore } from '../../store/useAuthStore';
import apiClient from '../../lib/apiClient';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.post('/auth/login/', { email, password });
      const { token, user } = response.data;
      
      await SecureStore.setItemAsync('authToken', token);
      setAuth(token, user);
      
      router.replace('/(tabs)/dashboard');
    } catch (error: any) {
      Alert.alert('Login Failed', error.response?.data?.error || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="flex-1 justify-center px-6 bg-brand-slate">
      <View className="items-center mb-10">
        <Text className="text-4xl font-bold text-white mb-2">Bluewave</Text>
        <Text className="text-brand-teal text-lg">Student Portal</Text>
      </View>

      <View className="space-y-4">
        <TextInput
          className="bg-white/10 text-white px-4 py-3 rounded-xl border border-white/20"
          placeholder="Email"
          placeholderTextColor="#9ca3af"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        
        <TextInput
          className="bg-white/10 text-white px-4 py-3 rounded-xl border border-white/20 mt-4"
          placeholder="Password"
          placeholderTextColor="#9ca3af"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity 
          className="bg-brand-blue py-4 rounded-xl mt-6 items-center flex-row justify-center"
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text className="text-white font-bold text-lg">Sign In</Text>
          )}
        </TouchableOpacity>
      </View>
      
      <View className="flex-row justify-center mt-6">
        <Text className="text-gray-400">Don't have an account? </Text>
        <TouchableOpacity onPress={() => router.push('/(auth)/register')}>
          <Text className="text-brand-teal font-semibold">Sign Up</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
