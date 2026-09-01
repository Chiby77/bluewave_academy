import { Tabs } from 'expo-router';
import { Home, BookOpen, MessageSquare, User } from 'lucide-react-native';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0F172A', // brand-slate
          borderTopColor: '#1e293b',
          height: 60,
          paddingBottom: 10,
        },
        tabBarActiveTintColor: '#14B8A6', // brand-teal
        tabBarInactiveTintColor: '#64748b',
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => <Home color={color} size={24} />,
        }}
      />
      <Tabs.Screen
        name="exams"
        options={{
          title: 'Exams',
          tabBarIcon: ({ color }) => <BookOpen color={color} size={24} />,
        }}
      />
      <Tabs.Screen
        name="tutor"
        options={{
          title: 'AI Tutor',
          tabBarIcon: ({ color }) => <MessageSquare color={color} size={24} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => <User color={color} size={24} />,
        }}
      />
    </Tabs>
  );
}
