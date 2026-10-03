import 'package:flutter/material.dart';
import 'screens/splash_screen.dart';
import 'screens/login_screen.dart';
import 'screens/etudiant_dashboard.dart';
import 'screens/pointage_screen.dart';
import 'screens/profil_screen.dart';

void main() {
  runApp(const IAMGPSApp());
}

class IAMGPSApp extends StatelessWidget {
  const IAMGPSApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'IAMGPS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF475569), // même bleu-gris ardoise que le site web
        ),
        scaffoldBackgroundColor: const Color(0xFFF5F6F9),
        useMaterial3: true,
      ),
      initialRoute: '/',
      routes: {
        '/':         (_) => SplashScreen(),
        '/login':    (_) => const LoginScreen(),
        '/etudiant': (_) => const EtudiantDashboard(),
        // Volontairement pas de route '/admin' ni '/enseignant' — ces deux rôles
        // se connectent maintenant sur le site web (frontend/iamgps-web/), pas
        // dans l'application mobile, qui est désormais réservée aux étudiants.
        '/pointage': (_) => const PointageScreen(),
        '/profil':   (_) => const ProfilScreen(),
      },
    );
  }
}