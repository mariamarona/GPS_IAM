import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

const Color kBg       = Color(0xFFF5F6F9);
const Color kNavy     = Color(0xFF111827);
const Color kBlue     = Color(0xFF475569);
const Color kBorder   = Color(0xFFE7E9EE);
const Color kTextMuted = Color(0xFF6B7280);
const Color kRed      = Color(0xFFDC2626);

/// Écran "Mon profil" — affiche les informations du compte connecté et permet de
/// se déconnecter. Les données viennent de SharedPreferences (déjà stockées au
/// moment de la connexion), donc aucun appel réseau n'est nécessaire ici.
class ProfilScreen extends StatefulWidget {
  const ProfilScreen({super.key});

  @override
  State<ProfilScreen> createState() => _ProfilScreenState();
}

class _ProfilScreenState extends State<ProfilScreen> {
  String _nom = '';
  String _prenom = '';
  String _matricule = '';
  String _role = '';
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _chargerProfil();
  }

  Future<void> _chargerProfil() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _nom = prefs.getString('user_nom') ?? '';
      _prenom = prefs.getString('user_prenom') ?? '';
      _matricule = prefs.getString('user_matricule') ?? '';
      _role = prefs.getString('user_role') ?? '';
      _isLoading = false;
    });
  }

  Future<void> _deconnexion() async {
    final confirme = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Déconnexion'),
        content: const Text('Voulez-vous vraiment vous déconnecter ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Déconnexion', style: TextStyle(color: kRed)),
          ),
        ],
      ),
    );

    if (confirme != true) return;

    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (mounted) Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
  }

  String get _nomComplet => '$_prenom $_nom'.trim();

  String get _initiales {
    final p = _prenom.isNotEmpty ? _prenom[0] : '';
    final n = _nom.isNotEmpty ? _nom[0] : '';
    return (p + n).toUpperCase();
  }

  String get _libelleRole {
    switch (_role.toUpperCase()) {
      case 'STUDENT':
        return 'Étudiant';
      case 'TEACHER':
        return 'Enseignant';
      default:
        return _role;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      appBar: AppBar(
        backgroundColor: kBg,
        elevation: 0,
        foregroundColor: kNavy,
        title: const Text('Mon profil', style: TextStyle(color: kNavy, fontWeight: FontWeight.bold)),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: kBlue))
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Center(
                  child: Container(
                    width: 84,
                    height: 84,
                    decoration: const BoxDecoration(color: kBlue, shape: BoxShape.circle),
                    child: Center(
                      child: Text(
                        _initiales,
                        style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                Center(
                  child: Text(_nomComplet,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: kNavy)),
                ),
                Center(
                  child: Text(_libelleRole, style: const TextStyle(fontSize: 13, color: kTextMuted)),
                ),
                const SizedBox(height: 28),

                _infoTile(icon: Icons.badge_outlined, label: 'Matricule', valeur: _matricule),
                _infoTile(icon: Icons.school_outlined, label: 'Rôle', valeur: _libelleRole),

                const SizedBox(height: 28),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _deconnexion,
                    icon: const Icon(Icons.logout, color: kRed, size: 18),
                    label: const Text('Déconnexion', style: TextStyle(color: kRed, fontWeight: FontWeight.w600)),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: kRed),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _infoTile({required IconData icon, required String label, required String valeur}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kBorder),
      ),
      child: Row(
        children: [
          Icon(icon, color: kBlue, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontSize: 11.5, color: kTextMuted)),
                Text(valeur.isEmpty ? '—' : valeur,
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: kNavy)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}