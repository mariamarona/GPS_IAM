import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'etudiant_dashboard.dart';

// ── URL de base (émulateur Android = 10.0.2.2, web/desktop = 127.0.0.1)
const String BASE_URL = 'http://192.168.1.99:8000';

// ── Couleurs officielles IAMGPS ─────────────────────────────────────────────
const Color kTeal       = Color(0xFF0D9B76);
const Color kTealDark   = Color(0xFF0B8764);
const Color kTealLight  = Color(0xFFE8FBF4);
const Color kDarkBg     = Color(0xFF0B1A2B);
const Color kDarkCard   = Color(0xFF111827);
const Color kDarkSurface= Color(0xFF1A2D3F);
const Color kNavy       = Color(0xFF1A3A4A);
const Color kTextMuted  = Color(0xFF64748B);

// ════════════════════════════════════════════════════════════════════════════
//  WIDGET PRINCIPAL
// ════════════════════════════════════════════════════════════════════════════
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with TickerProviderStateMixin {

  // ── Contrôleurs ────────────────────────────────────────────────────────────
  final _formKey            = GlobalKey<FormState>();
  final _emailCtrl          = TextEditingController();
  final _passwordCtrl       = TextEditingController();

  // ── État ───────────────────────────────────────────────────────────────────
  bool _isLoading           = false;
  bool _obscurePassword     = true;
  String? _errorMessage;
  String _selectedRole      = 'STUDENT'; // STUDENT | TEACHER | ADMIN

  // ── Animations ─────────────────────────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late AnimationController _pulseCtrl;
  late Animation<double>   _fadeAnim;
  late Animation<double>   _slideAnim;
  late Animation<double>   _pulseAnim;
  late Animation<double>   _cardFadeAnim;

  @override
  void initState() {
    super.initState();

    _fadeCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    _fadeAnim = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _fadeCtrl, curve: const Interval(0.0, 0.5, curve: Curves.easeOut)),
    );
    _slideAnim = Tween<double>(begin: 30, end: 0).animate(
      CurvedAnimation(parent: _fadeCtrl, curve: const Interval(0.0, 0.6, curve: Curves.easeOut)),
    );
    _cardFadeAnim = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _fadeCtrl, curve: const Interval(0.3, 1.0, curve: Curves.easeOut)),
    );
    _pulseAnim = Tween<double>(begin: 0.6, end: 1.0).animate(
      CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut),
    );

    _fadeCtrl.forward();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _pulseCtrl.dispose();
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  // ── API Login ───────────────────────────────────────────────────────────────
  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() { _isLoading = true; _errorMessage = null; });

    try {
      final response = await http.post(
        Uri.parse('$BASE_URL/api/auth/login/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email':        _emailCtrl.text.trim(),
          'mot_de_passe': _passwordCtrl.text,
        }),
      ).timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final user = data['utilisateur'] ?? data['user'];
        final role = (user['role'] as String).toUpperCase();

        // L'application mobile est désormais réservée aux étudiants — l'admin et
        // l'enseignant utilisent le site web. On ne stocke pas la session ni ne
        // navigue pour ces rôles-là depuis l'appli mobile.
        if (role == 'ADMIN' || role == 'SUPER_ADMIN' || role == 'TEACHER' || role == 'ENSEIGNANT') {
          setState(() {
            _errorMessage = role == 'TEACHER' || role == 'ENSEIGNANT'
                ? "Les comptes enseignant se connectent désormais sur le site web, pas sur l'application mobile."
                : "Les comptes administrateur ne sont pas pris en charge dans l'application mobile — "
                  "utilisez le site web pour l'administration.";
          });
          return;
        }

        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token',   data['access']);
        await prefs.setString('refresh_token',  data['refresh']);
        await prefs.setString('user_role',      user['role']);
        await prefs.setString('user_id',        user['id'].toString());
        await prefs.setString('user_nom',       user['nom']);
        await prefs.setString('user_prenom',    user['prenom']);
        await prefs.setString('user_matricule', user['matricule']);

        if (!mounted) return;
        _naviguerSelonRole(user['role']);
      } else {
        setState(() {
          _errorMessage = data['detail'] ?? data['error'] ?? 'Identifiant ou mot de passe incorrect.';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Impossible de contacter le serveur. Vérifiez votre connexion réseau.';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _naviguerSelonRole(String role) {
    // Garde-fou : à ce stade, seul un rôle STUDENT devrait pouvoir arriver ici
    // (ADMIN/TEACHER sont interceptés plus haut avant même le stockage de la
    // session) — mais on reste défensif plutôt que de risquer d'exposer un écran
    // qui n'a plus lieu d'être dans l'appli mobile.
    if (role.toUpperCase() != 'STUDENT') {
      setState(() {
        _errorMessage = "Ce rôle n'est plus pris en charge dans l'application mobile.";
      });
      return;
    }
    Widget destination = const EtudiantDashboard();
    Navigator.pushReplacement(
      context,
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => destination,
        transitionsBuilder: (_, anim, __, child) =>
            FadeTransition(opacity: anim, child: child),
        transitionDuration: const Duration(milliseconds: 400),
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  BUILD
  // ══════════════════════════════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: kDarkBg,
      body: Stack(
        children: [
          // ── Fond décoratif ─────────────────────────────────────────────
          _buildBackground(size),

          // ── Contenu principal ──────────────────────────────────────────
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Column(
                children: [
                  const SizedBox(height: 32),
                  _buildLogo(),
                  const SizedBox(height: 32),
                  _buildCard(),
                  const SizedBox(height: 24),
                  _buildFooter(),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),

          // ── Indicateur GPS actif ───────────────────────────────────────
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            right: 16,
            child: _buildGpsIndicator(),
          ),
        ],
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  FOND DÉCORATIF
  // ══════════════════════════════════════════════════════════════════════════
  Widget _buildBackground(Size size) {
    return Stack(
      children: [
        // Grille de points subtile
        CustomPaint(
          size: size,
          painter: _GridPainter(),
        ),
        // Halo teal haut-gauche
        Positioned(
          top: -100, left: -80,
          child: Container(
            width: 350, height: 350,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(colors: [
                kTeal.withOpacity(0.12),
                Colors.transparent,
              ]),
            ),
          ),
        ),
        // Halo bas-droite
        Positioned(
          bottom: -80, right: -60,
          child: Container(
            width: 300, height: 300,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(colors: [
                kTeal.withOpacity(0.08),
                Colors.transparent,
              ]),
            ),
          ),
        ),
      ],
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  INDICATEUR GPS
  // ══════════════════════════════════════════════════════════════════════════
  Widget _buildGpsIndicator() {
    return AnimatedBuilder(
      animation: _pulseAnim,
      builder: (_, __) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: kTeal.withOpacity(0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: kTeal.withOpacity(0.35)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 7, height: 7,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: kTeal.withOpacity(_pulseAnim.value),
              ),
            ),
            //const SizedBox(width: 6),
            //const Text(
             // 'Système actif',
             // style: TextStyle(fontSize: 11, color: kTeal, fontWeight: FontWeight.w500),
            //),
          ],
        ),
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  LOGO
  // ══════════════════════════════════════════════════════════════════════════
  Widget _buildLogo() {
    return AnimatedBuilder(
      animation: _fadeCtrl,
      builder: (_, __) => Opacity(
        opacity: _fadeAnim.value,
        child: Transform.translate(
          offset: Offset(0, _slideAnim.value),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Icône GPS SVG custom
              _buildGpsIcon(size: 50),
              const SizedBox(width: 14),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  RichText(
                    text: const TextSpan(
                      children: [
                        TextSpan(
                          text: 'IAM',
                          style: TextStyle(
                            fontSize: 32, fontWeight: FontWeight.w900,
                            color: kTeal, letterSpacing: -1,
                            fontFamily: 'Roboto',
                          ),
                        ),
                        TextSpan(
                          text: 'GPS',
                          style: TextStyle(
                            fontSize: 32, fontWeight: FontWeight.w900,
                            color: Colors.white, letterSpacing: -1,
                            fontFamily: 'Roboto',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Text(
                    'PRÉSENCE · IA · SÉCURITÉ',
                    style: TextStyle(
                      fontSize: 9.5, color: Color(0xFF4A7A9B),
                      letterSpacing: 2.5, fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Icône GPS dessinée avec CustomPaint
  Widget _buildGpsIcon({double size = 44}) {
    return SizedBox(
      width: size, height: size,
      child: CustomPaint(painter: _GpsIconPainter()),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  CARTE CONNEXION
  // ══════════════════════════════════════════════════════════════════════════
  Widget _buildCard() {
    return AnimatedBuilder(
      animation: _fadeCtrl,
      builder: (_, child) => Opacity(
        opacity: _cardFadeAnim.value,
        child: Transform.translate(
          offset: Offset(0, _slideAnim.value * 0.6),
          child: child,
        ),
      ),
      child: Container(
        width: double.infinity,
        constraints: const BoxConstraints(maxWidth: 440),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: kTeal.withOpacity(0.15)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.25),
              blurRadius: 40,
              offset: const Offset(0, 16),
            ),
            BoxShadow(
              color: kTeal.withOpacity(0.06),
              blurRadius: 60,
              spreadRadius: -10,
            ),
          ],
        ),
        padding: const EdgeInsets.fromLTRB(32, 36, 32, 32),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [

              // Titre
              const Center(
                child: Text(
                  'Connexion',
                  style: TextStyle(
                    fontSize: 22, fontWeight: FontWeight.w700,
                    color: kNavy, letterSpacing: -0.3,
                  ),
                ),
              ),
              const SizedBox(height: 4),
              const Center(
                child: Text(
                  'Accédez à votre espace IAMGPS',
                  style: TextStyle(fontSize: 13, color: kTextMuted),
                ),
              ),
              const SizedBox(height: 24),

              // Alerte erreur
              if (_errorMessage != null) ...[
                _buildErrorBanner(),
                const SizedBox(height: 14),
              ],

              // Champ email
              _buildFieldLabel('Identifiant / Email'),
              const SizedBox(height: 6),
              _buildTextField(
                controller: _emailCtrl,
                hint: '',
                icon: Icons.person_outline_rounded,
                keyboardType: TextInputType.emailAddress,
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Identifiant requis';
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Champ mot de passe
              _buildFieldLabel('Mot de passe'),
              const SizedBox(height: 6),
              _buildTextField(
                controller: _passwordCtrl,
                hint: '',
                icon: Icons.lock_outline_rounded,
                isPassword: true,
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Mot de passe requis';
                  if (v.length < 6) return 'Minimum 6 caractères';
                  return null;
                },
              ),
              const SizedBox(height: 14),

              // Remember + Forgot
              _buildRememberRow(),
              const SizedBox(height: 22),

              // Bouton connexion
              _buildLoginButton(),
              const SizedBox(height: 20),

              // Divider
              _buildDivider('Système sécurisé'),
              const SizedBox(height: 16),

              // Info GPS
              _buildInfoBox(),
            ],
          ),
        ),
      ),
    );
  }

  // ── Sélecteur de rôle ────────────────────────────────────────────────────
  Widget _buildRoleSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'VOTRE PROFIL',
          style: TextStyle(fontSize: 10.5, color: kTextMuted,
              letterSpacing: 1, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            _roleChip('STUDENT',    Icons.school_outlined,      'Étudiant'),
            const SizedBox(width: 8),
            _roleChip('TEACHER',    Icons.co_present_outlined,  'Enseignant'),
            const SizedBox(width: 8),
            _roleChip('ADMIN',      Icons.shield_outlined,      'Admin'),
          ],
        ),
      ],
    );
  }

  Widget _roleChip(String role, IconData icon, String label) {
    final selected = _selectedRole == role;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() {
          _selectedRole = role;
          _errorMessage = null;
        }),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? kTealLight : const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected ? kTeal : const Color(0xFFE2E8F0),
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Column(
            children: [
              Icon(icon, size: 20, color: selected ? kTeal : kTextMuted),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 10, fontWeight: FontWeight.w600,
                  color: selected ? kTeal : kTextMuted,
                  letterSpacing: .3,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Label champ ──────────────────────────────────────────────────────────
  Widget _buildFieldLabel(String label) {
    return Text(
      label,
      style: const TextStyle(
        fontSize: 12, fontWeight: FontWeight.w500,
        color: kNavy, letterSpacing: .3,
      ),
    );
  }

  // ── Champ texte ──────────────────────────────────────────────────────────
  Widget _buildTextField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    bool isPassword = false,
    TextInputType keyboardType = TextInputType.text,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: isPassword ? _obscurePassword : false,
      keyboardType: keyboardType,
      style: const TextStyle(fontSize: 14, color: kNavy),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: Color(0xFFB0BEC5), fontSize: 13),
        prefixIcon: Icon(icon, color: kTeal, size: 20),
        suffixIcon: isPassword
            ? IconButton(
                icon: Icon(
                  _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                  color: const Color(0xFF94A3B8), size: 20,
                ),
                onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
              )
            : null,
        filled: true,
        fillColor: const Color(0xFFF8FAFC),
        contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: kTeal, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Colors.red, width: 1.2),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Colors.red, width: 1.5),
        ),
        errorStyle: const TextStyle(fontSize: 11),
      ),
      validator: validator,
    );
  }

  // ── Remember / Forgot ────────────────────────────────────────────────────
  Widget _buildRememberRow() {
    return Row(
      children: [
        SizedBox(
          height: 18, width: 18,
          child: Checkbox(
            value: false,
            activeColor: kTeal,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
            onChanged: (_) {},
          ),
        ),
        const SizedBox(width: 8),
        const Text('Se souvenir de moi',
            style: TextStyle(fontSize: 13, color: kTextMuted)),
        const Spacer(),
        GestureDetector(
          onTap: () => setState(() => _errorMessage =
              'Un lien de réinitialisation sera envoyé à votre email institutionnel.'),
          child: const Text(
            'Mot de passe oublié ?',
            style: TextStyle(fontSize: 13, color: kTeal, fontWeight: FontWeight.w500),
          ),
        ),
      ],
    );
  }

  // ── Bouton connexion ─────────────────────────────────────────────────────
  Widget _buildLoginButton() {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: ElevatedButton(
        onPressed: _isLoading ? null : _login,
        style: ElevatedButton.styleFrom(
          backgroundColor: kTeal,
          disabledBackgroundColor: kTealDark,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        child: _isLoading
            ? const SizedBox(
                width: 22, height: 22,
                child: CircularProgressIndicator(
                  color: Colors.white, strokeWidth: 2.2),
              )
            : const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.login_rounded, size: 18),
                  SizedBox(width: 8),
                  Text(
                    'SE CONNECTER',
                    style: TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w700,
                      letterSpacing: .5,
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  // ── Bannière erreur ──────────────────────────────────────────────────────
  Widget _buildErrorBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF2F2),
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: Colors.red, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _errorMessage!,
              style: const TextStyle(fontSize: 12, color: Color(0xFF991B1B)),
            ),
          ),
          GestureDetector(
            onTap: () => setState(() => _errorMessage = null),
            child: const Icon(Icons.close_rounded, color: Colors.red, size: 16),
          ),
        ],
      ),
    );
  }

  // ── Divider ──────────────────────────────────────────────────────────────
  Widget _buildDivider(String text) {
    return Row(
      children: [
        Expanded(child: Container(height: 1, color: const Color(0xFFE2E8F0))),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Text(text,
              style: const TextStyle(fontSize: 11, color: Color(0xFFB0BEC5))),
        ),
        Expanded(child: Container(height: 1, color: const Color(0xFFE2E8F0))),
      ],
    );
  }

  // ── Info box GPS ─────────────────────────────────────────────────────────
  Widget _buildInfoBox() {
    return Container(
      //padding: const EdgeInsets.all(12),
      //decoration: BoxDecoration(
        //color: kTealLight,
       // borderRadius: BorderRadius.circular(9),
       // border: Border.all(color: kTeal.withOpacity(0.25)),
      //),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
         // Icon(Icons.location_on_outlined, color: kTeal, size: 16),
          //SizedBox(width: 8),
          //Expanded(
            //child: Text(
             // 'Le pointage GPS requiert l\'activation de la localisation sur votre appareil. '
             // 'Vos données sont chiffrées et protégées.',
             // style: TextStyle(fontSize: 11.5, color: Color(0xFF0F6E56), height: 1.5),
           //),//
          //),
       ],
      ),
    );
  }

  // ── Footer ───────────────────────────────────────────────────────────────
  Widget _buildFooter() {
    return AnimatedBuilder(
      animation: _fadeCtrl,
      builder: (_, __) => Opacity(
        opacity: _cardFadeAnim.value,
        child: Column(
          children: const [
            Text(
              'IAMGPS v1.0.0 — 2026 © Institut Africain de Management',
              style: TextStyle(fontSize: 11, color: Color(0xFF4A7A9B)),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 4),
            Text(
              'Système de Gestion de Présence par GPS et IA',
              style: TextStyle(fontSize: 10.5, color: Color(0xFF2D5A6E)),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ════════════════════════════════════════════════════════════════════════════
//  CUSTOM PAINTERS
// ════════════════════════════════════════════════════════════════════════════

/// Grille de points de fond
class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF0D9B76).withOpacity(0.04)
      ..strokeWidth = 1;
    const step = 40.0;
    for (double x = 0; x < size.width; x += step) {
      for (double y = 0; y < size.height; y += step) {
        canvas.drawCircle(Offset(x, y), 1.5, paint);
      }
    }
  }
  @override
  bool shouldRepaint(_) => false;
}

/// Icône GPS (cercle + point + tige + ondes)
class _GpsIconPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final teal   = const Color(0xFF0D9B76);
    final cx     = size.width / 2;
    final cy     = size.height / 2;
    final radius = size.width / 2 - 2;

    final strokePaint = Paint()
      ..color = teal
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;

    final fillPaint = Paint()
      ..color = teal
      ..style = PaintingStyle.fill;

    // Cercle contour
    canvas.drawCircle(Offset(cx, cy), radius, strokePaint);

    // Point GPS (haut)
    final dotY = cy - radius * 0.35;
    canvas.drawCircle(Offset(cx, dotY), radius * 0.22, fillPaint);

    // Reflet blanc
    final reflectPaint = Paint()
      ..color = Colors.white.withOpacity(0.4)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(cx - radius * 0.06, dotY - radius * 0.06),
        radius * 0.08, reflectPaint);

    // Tige
    canvas.drawLine(
      Offset(cx, dotY + radius * 0.22),
      Offset(cx, cy + radius * 0.35),
      strokePaint..strokeWidth = 3.5,
    );

    // Onde gauche
    final wavePaint = Paint()
      ..color = teal.withOpacity(0.45)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;

    final path1 = Path()
      ..moveTo(cx - radius * 0.35, dotY)
      ..quadraticBezierTo(
        cx - radius * 0.6, cy,
        cx - radius * 0.35, cy + radius * 0.35,
      );
    canvas.drawPath(path1, wavePaint);

    // Onde droite
    final path2 = Path()
      ..moveTo(cx + radius * 0.35, dotY)
      ..quadraticBezierTo(
        cx + radius * 0.6, cy,
        cx + radius * 0.35, cy + radius * 0.35,
      );
    canvas.drawPath(path2, wavePaint);
  }

  @override
  bool shouldRepaint(_) => false;
}