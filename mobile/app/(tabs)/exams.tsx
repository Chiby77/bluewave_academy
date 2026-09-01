import { View, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function ExamsTab() {
  return (
    <SafeAreaView className="flex-1 bg-brand-slate justify-center items-center">
      <Text className="text-white text-2xl font-bold">Exams Hub</Text>
      <Text className="text-gray-400 mt-2">View all your exams here.</Text>
    </SafeAreaView>
  );
}
