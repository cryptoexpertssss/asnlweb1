import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
} from 'react-native';
import MapView, { Marker } from 'react-native-maps';
import * as Location from 'expo-location';
import { useRouter } from 'expo-router';
import axios from 'axios';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Salon {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  rating: number;
}

export default function MapScreen() {
  const router = useRouter();
  const [location, setLocation] = useState<any>(null);
  const [salons, setSalons] = useState<Salon[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMapData();
  }, []);

  const loadMapData = async () => {
    try {
      // Request location permission
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Location permission is required to show nearby salons');
        setLoading(false);
        return;
      }

      // Get current location
      const currentLocation = await Location.getCurrentPositionAsync({});
      setLocation({
        latitude: currentLocation.coords.latitude,
        longitude: currentLocation.coords.longitude,
        latitudeDelta: 0.05,
        longitudeDelta: 0.05,
      });

      // Load salons
      const response = await axios.get(`${BACKEND_URL}/api/salons`);
      setSalons(response.data);
    } catch (error) {
      console.error('Error loading map data:', error);
      // Set default location (Islamabad)
      setLocation({
        latitude: 33.6844,
        longitude: 73.0479,
        latitudeDelta: 0.05,
        longitudeDelta: 0.05,
      });
      // Load salons anyway
      try {
        const response = await axios.get(`${BACKEND_URL}/api/salons`);
        setSalons(response.data);
      } catch (err) {
        console.error('Error loading salons:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#FF69B4" />
        <Text style={styles.loadingText}>Loading map...</Text>
      </View>
    );
  }

  if (!location) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Unable to load map</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadMapData}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Nearby Salons</Text>
      </View>

      <MapView style={styles.map} initialRegion={location} showsUserLocation showsMyLocationButton>
        {salons.map((salon) => (
          <Marker
            key={salon.id}
            coordinate={{
              latitude: salon.latitude,
              longitude: salon.longitude,
            }}
            title={salon.name}
            description={`Rating: ${salon.rating} ⭐`}
            pinColor="#FF69B4"
            onCalloutPress={() => router.push(`/salon/${salon.id}`)}
          />
        ))}
      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    padding: 24,
  },
  errorText: {
    fontSize: 16,
    color: '#666',
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: '#FF69B4',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    backgroundColor: '#FF69B4',
    paddingTop: 60,
    paddingBottom: 16,
    paddingHorizontal: 24,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  map: {
    flex: 1,
  },
});
