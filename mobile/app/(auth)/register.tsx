import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import { useAuthStore } from '../../store/useAuthStore';
import apiClient from '../../lib/apiClient';

export default function RegisterScreen() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const handleRegister = async () => {
    if (!email || !password || !firstName || !lastName) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.post('/auth/register/', { 
        email, 
        password,
        first_name: firstName,
        last_name: lastName
      });
      const { token, user } = response.data;
      
      await SecureStore.setItemAsync('authToken', token);
      setAuth(token, user);
      
      router.replace('/(tabs)/dashboard');
    } catch (error: any) {
      Alert.alert('Registration Failed', error.response?.data?.error || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="flex-1 justify-center px-6 bg-brand-slate">
      <View className="items-center mb-10">
        <Text className="text-3xl font-bold text-white mb-2">Create Account</Text>
        <Text className="text-gray-400">Join Bluewave Academy</Text>
      </View>

      <View className="space-y-4">
        <TextInput
          className="bg-white/10 text-white px-4 py-3 rounded-xl border border-white/20"
          placeholder="First Name"
          placeholderTextColor="#9ca3af"
          value={firstName}
          onChangeText={setFirstName}
        />
        
        <TextInput
          className="bg-white/10 text-white px-4 py-3 rounded-xl border border-white/20 mt-4"
          placeholder="Last Name"
          placeholderTextColor="#9ca3af"
          value={lastName}
          onChangeText={setLastName}
        />

        <TextInput
          className="bg-white/10 text-white px-4 py-3 rounded-xl border border-white/20 mt-4"
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
          onPress={handleRegister}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text className="text-white font-bold text-lg">Sign Up</Text>
          )}
        </TouchableOpacity>
      </View>
      
      <View className="flex-row justify-center mt-6">
        <Text className="text-gray-400">Already have an account? </Text>
        <TouchableOpacity onPress={() => router.push('/(auth)/login')}>
          <Text className="text-brand-teal font-semibold">Sign In</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
