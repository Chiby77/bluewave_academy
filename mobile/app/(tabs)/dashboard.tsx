import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../lib/apiClient';
import { useRouter } from 'expo-router';

export default function DashboardScreen() {
  const router = useRouter();

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const response = await apiClient.get('/dashboard/');
      return response.data;
    },
  });

  if (isLoading && !isRefetching) {
    return (
      <SafeAreaView className="flex-1 bg-brand-slate justify-center items-center">
        <ActivityIndicator size="large" color="#14B8A6" />
      </SafeAreaView>
    );
  }

  if (isError) {
    return (
      <SafeAreaView className="flex-1 bg-brand-slate justify-center items-center">
        <Text className="text-red-400">Failed to load dashboard.</Text>
        <TouchableOpacity onPress={() => refetch()} className="mt-4 bg-brand-blue px-4 py-2 rounded-lg">
          <Text className="text-white">Retry</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-brand-slate" edges={['top']}>
      <ScrollView 
        className="flex-1 px-4"
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => { refetch(); }} tintColor="#14B8A6" />}
      >
        <View className="py-6">
          <Text className="text-white text-3xl font-bold">Hello, {data?.user?.first_name || 'Student'} 👋</Text>
          <Text className="text-gray-400 mt-2">Ready to learn something new today?</Text>
        </View>

        <View className="mt-4">
          <Text className="text-xl font-bold text-white mb-4">Recent Exams</Text>
          {data?.recent_attempts?.length === 0 ? (
            <Text className="text-gray-500">No recent exam attempts.</Text>
          ) : (
            data?.recent_attempts?.map((attempt: any) => (
              <TouchableOpacity 
                key={attempt.id} 
                className="bg-white/5 p-4 rounded-xl border border-white/10 mb-3 flex-row justify-between items-center"
                onPress={() => router.push(`/exams/result/${attempt.id}`)}
              >
                <View>
                  <Text className="text-white font-semibold text-lg">{attempt.exam_title}</Text>
                  <Text className="text-gray-400 capitalize">{attempt.status.replace('_', ' ')}</Text>
                </View>
                <View className="bg-brand-blue/20 px-3 py-1 rounded-full">
                  <Text className="text-brand-blue font-bold">
                    {attempt.score !== null ? `${attempt.score}%` : '---'}
                  </Text>
                </View>
              </TouchableOpacity>
            ))
          )}
        </View>

        <View className="mt-8 mb-8">
          <Text className="text-xl font-bold text-white mb-4">Available Exams</Text>
          {data?.available_exams?.length === 0 ? (
            <Text className="text-gray-500">No exams available right now.</Text>
          ) : (
            data?.available_exams?.map((exam: any) => (
              <TouchableOpacity 
                key={exam.id} 
                className="bg-brand-blue p-5 rounded-2xl mb-3 flex-row justify-between items-center"
                onPress={() => router.push(`/exams/take/${exam.id}`)}
              >
                <View>
                  <Text className="text-white font-bold text-lg">{exam.title}</Text>
                  <Text className="text-blue-200 mt-1">{exam.duration_minutes} Minutes</Text>
                </View>
                <View className="bg-white/20 px-4 py-2 rounded-xl">
                  <Text className="text-white font-bold">Take</Text>
                </View>
              </TouchableOpacity>
            ))
          )}
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}
