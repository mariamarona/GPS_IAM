import 'package:flutter/material.dart';
import 'login_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {

  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();

    // Animation fade + scale
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeIn),
    );

    _scaleAnimation = Tween<double>(begin: 0.7, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.elasticOut),
    );

    _controller.forward();

    // Redirection vers login après 3 secondes
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const LoginScreen()),
        );
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Center(
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: ScaleTransition(
            scale: _scaleAnimation,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [

                // ── Logo ─────────────────────────────────
                // Remplace l'ancienne image (assets/images/logo.jpeg, absente/vide
                // du projet et provoquant une erreur au démarrage) par une icône
                // simple, qui ne dépend d'aucun fichier externe.
                Container(
                  width: 96,
                  height: 96,
                  decoration: BoxDecoration(
                    color: const Color(0xFF475569),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: const Icon(Icons.location_on, color: Colors.white, size: 52),
                ),

                const SizedBox(height: 24),

                // ── Nom de l'application ─────────────────
                const Text(
                  'IAMGPS',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF475569),  // bleu-gris ardoise (identité du site web)
                    letterSpacing: 4,
                  ),
                ),

                const SizedBox(height: 8),

                const Text(
                  'Système de Pointage GPS',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey,
                    letterSpacing: 1,
                  ),
                ),

                const SizedBox(height: 48),

                // ── Indicateur de chargement ─────────────
                const CircularProgressIndicator(
                  color: Color(0xFF475569),
                  strokeWidth: 2,
                ),

              ],
            ),
          ),
        ),
      ),
    );
  }
}