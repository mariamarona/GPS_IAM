import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const String BASE_URL = 'http://192.168.1.99:8000';

// ── Palette IAMGPS (reprise du site web) ──────────────────────
const Color kNavy       = Color(0xFF111827);
const Color kNavySoft   = Color(0xFF1C2537);
const Color kNavyBorder = Color(0xFF263042);
const Color kBg         = Color(0xFFF5F6F9);
const Color kBlue       = Color(0xFF2563EB);
const Color kBlueLight  = Color(0xFFDBEAFE);
const Color kGreen      = Color(0xFF16A34A);
const Color kGreenLight = Color(0xFFDCFCE7);
const Color kRed        = Color(0xFFDC2626);
const Color kRedLight   = Color(0xFFFEE2E2);
const Color kOrange     = Color(0xFFD97706);
const Color kOrangeLight= Color(0xFFFEF3C7);
const Color kPurple     = Color(0xFF9333EA);
const Color kPurpleLight= Color(0xFFF3E8FF);
const Color kTextMuted  = Color(0xFF6B7280);

class EtudiantDashboard extends StatefulWidget {
  const EtudiantDashboard({super.key});

  @override
  State<EtudiantDashboard> createState() => _EtudiantDashboardState();
}

class _EtudiantDashboardState extends State<EtudiantDashboard> {
  Map<String, dynamic>? _data;
  bool _isLoading = true;
  String? _error;

  String _nom      = '';
  String _prenom   = '';
  String _matricule = '';
  String _userId   = '';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final prefs = await SharedPreferences.getInstance();
    _userId    = prefs.getString('user_id') ?? '';
    _nom       = prefs.getString('user_nom') ?? '';
    _prenom    = prefs.getString('user_prenom') ?? '';
    _matricule = prefs.getString('user_matricule') ?? '';
    final token = prefs.getString('access_token') ?? '';

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await http.get(
        Uri.parse('$BASE_URL/api/dashboard/etudiant/?utilisateur_id=$_userId'),
        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
      );

      if (res.statusCode == 200) {
        setState(() {
          _data = jsonDecode(res.body);
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = 'Erreur ${res.statusCode} lors du chargement.';
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Impossible de contacter le serveur.';
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (mounted) Navigator.pushReplacementNamed(context, '/login');
  }

  @override
  Widget build(BuildContext context) {
    final large = MediaQuery.of(context).size.width >= 800;

    return Scaffold(
      backgroundColor: kBg,
      appBar: large
          ? null
          : AppBar(
              backgroundColor: kNavy,
              iconTheme: const IconThemeData(color: Colors.white),
              title: const Text('IAMGPS', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
      drawer: large ? null : Drawer(child: _buildSidebarContent()),
      body: SafeArea(
        child: Row(
          children: [
            if (large)
              SizedBox(
                width: 260,
                child: _buildSidebarContent(),
              ),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: kBlue))
                  : _error != null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(_error!, style: const TextStyle(color: kRed), textAlign: TextAlign.center),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadData,
                          child: ListView(
                            padding: const EdgeInsets.all(24),
                            children: [
                              _buildHeader(),
                              const SizedBox(height: 24),
                              _buildStatsGrid(),
                              const SizedBox(height: 20),
                              _buildEvolutionCard(),
                              const SizedBox(height: 20),
                              _buildProchainsCoursCard(),
                              const SizedBox(height: 20),
                              _buildHistoriqueCard(),
                            ],
                          ),
                        ),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────
  //  SIDEBAR
  // ─────────────────────────────────────────────
  Widget _buildSidebarContent() {
    return Container(
      color: kNavy,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(color: kBlue, borderRadius: BorderRadius.circular(10)),
                child: const Icon(Icons.location_on, color: Colors.white, size: 20),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('IAMGPS', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                    Text('Présence & Détection IA', style: TextStyle(color: Color(0xFF8A93A6), fontSize: 10)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: kNavySoft,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: kNavyBorder),
            ),
            child: const Row(
              children: [
                Icon(Icons.school_rounded, color: kBlue, size: 16),
                SizedBox(width: 8),
                Text('Espace Étudiant', style: TextStyle(color: Color(0xFFDBE1EC), fontSize: 12, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          const SizedBox(height: 18),
          _sidebarItem(icon: Icons.grid_view_rounded, label: 'Tableau de bord', selected: true, onTap: () {
            // Déjà sur cet écran — rien à faire.
          }),
          _sidebarItem(icon: Icons.my_location_rounded, label: 'Pointer ma présence', selected: false, onTap: () {
            Navigator.pushNamed(context, '/pointage');
          }),
          _sidebarItem(icon: Icons.person_outline_rounded, label: 'Mon profil', selected: false, onTap: () {
            Navigator.pushNamed(context, '/profil');
          }),
          const Spacer(),
          Container(height: 1, color: kNavyBorder),
          const SizedBox(height: 14),
          Row(
            children: [
              CircleAvatar(
                radius: 17,
                backgroundColor: kNavySoft,
                child: Text(
                  _prenom.isNotEmpty ? _prenom[0].toUpperCase() : 'E',
                  style: const TextStyle(color: Color(0xFFCBD2E0), fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('$_prenom $_nom',
                        style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis),
                    Text(_matricule, style: const TextStyle(color: Color(0xFF8A93A6), fontSize: 11)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          TextButton.icon(
            onPressed: _logout,
            icon: const Icon(Icons.logout, size: 16, color: Color(0xFFAAB2C2)),
            label: const Text('Déconnexion', style: TextStyle(color: Color(0xFFAAB2C2), fontSize: 13)),
            style: TextButton.styleFrom(alignment: Alignment.centerLeft, padding: EdgeInsets.zero),
          ),
        ],
      ),
    );
  }

  Widget _sidebarItem({required IconData icon, required String label, required bool selected, required VoidCallback onTap}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Material(
        color: selected ? kBlue.withOpacity(0.2) : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
            child: Row(
              children: [
                Icon(icon, size: 18, color: selected ? const Color(0xFF60A5FA) : const Color(0xFFAAB2C2)),
                const SizedBox(width: 12),
                Text(label,
                    style: TextStyle(
                      color: selected ? const Color(0xFF60A5FA) : const Color(0xFFAAB2C2),
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                    )),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────
  //  CONTENU
  // ─────────────────────────────────────────────
  Widget _buildHeader() {
    final nomComplet = '$_prenom $_nom'.trim();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Bonjour, $nomComplet 👋',
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: kNavy)),
        const SizedBox(height: 4),
        const Text('Voici votre résumé de présence', style: TextStyle(color: kTextMuted, fontSize: 14)),
      ],
    );
  }

  Widget _buildStatsGrid() {
    final stats = _data?['stats'] ?? {};
    final items = [
      {'label': 'Taux de présence', 'value': '${stats['taux_presence'] ?? 0}%', 'icon': Icons.trending_up_rounded, 'bg': kBlueLight, 'fg': kBlue},
      {'label': 'Présences', 'value': '${stats['total_present'] ?? 0}', 'icon': Icons.check_circle_rounded, 'bg': kGreenLight, 'fg': kGreen},
      {'label': 'Absences', 'value': '${stats['total_absent'] ?? 0}', 'icon': Icons.cancel_rounded, 'bg': kRedLight, 'fg': kRed},
      {'label': 'Total séances', 'value': '${stats['total_sessions'] ?? 0}', 'icon': Icons.calendar_month_rounded, 'bg': kPurpleLight, 'fg': kPurple},
    ];

    return LayoutBuilder(builder: (context, constraints) {
      final cols = constraints.maxWidth >= 700 ? 4 : 2;
      return GridView.count(
        crossAxisCount: cols,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisSpacing: 14,
        mainAxisSpacing: 14,
        childAspectRatio: 1.5,
        children: items.map((it) => _statCard(
          label: it['label'] as String,
          value: it['value'] as String,
          icon: it['icon'] as IconData,
          bg: it['bg'] as Color,
          fg: it['fg'] as Color,
        )).toList(),
      );
    });
  }

  Widget _statCard({required String label, required String value, required IconData icon, required Color bg, required Color fg}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE7E9EE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Container(
            width: 34, height: 34,
            decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(8)),
            child: Icon(icon, color: fg, size: 18),
          ),
          Text(label, style: const TextStyle(fontSize: 11.5, color: kTextMuted)),
          Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: kNavy)),
        ],
      ),
    );
  }

  Widget _card({required String title, required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE7E9EE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: kNavy)),
          const SizedBox(height: 16),
          child,
        ],
      ),
    );
  }

  Widget _buildEvolutionCard() {
    final List<dynamic> evolution = _data?['evolution'] ?? [];

    if (evolution.length < 2) {
      return _card(
        title: 'Évolution du taux de présence (par semaine)',
        child: SizedBox(
          height: 100,
          child: Center(
            child: Text(
              evolution.isEmpty
                  ? 'Pas encore de données de présence.'
                  : 'Une seule semaine de données pour l\'instant — le graphique se remplira au fil des semaines.',
              style: const TextStyle(color: kTextMuted, fontSize: 12.5),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    final spots = <FlSpot>[];
    for (var i = 0; i < evolution.length; i++) {
      final taux = (evolution[i]['taux'] as num).toDouble();
      spots.add(FlSpot(i.toDouble(), taux));
    }

    return _card(
      title: 'Évolution du taux de présence (par semaine)',
      child: SizedBox(
        height: 200,
        child: LineChart(
          LineChartData(
            minY: 0,
            maxY: 100,
            gridData: FlGridData(show: true, drawVerticalLine: false, horizontalInterval: 20),
            borderData: FlBorderData(show: false),
            titlesData: FlTitlesData(
              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              leftTitles: AxisTitles(
                sideTitles: SideTitles(showTitles: true, reservedSize: 32, interval: 20,
                    getTitlesWidget: (v, meta) => Text('${v.toInt()}', style: const TextStyle(fontSize: 10, color: kTextMuted))),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  getTitlesWidget: (v, meta) {
                    final idx = v.toInt();
                    if (idx < 0 || idx >= evolution.length) return const SizedBox.shrink();
                    final periode = evolution[idx]['periode'] as String;
                    return Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(periode.substring(5), style: const TextStyle(fontSize: 10, color: kTextMuted)),
                    );
                  },
                ),
              ),
            ),
            lineBarsData: [
              LineChartBarData(
                spots: spots,
                isCurved: true,
                color: kBlue,
                barWidth: 3,
                dotData: const FlDotData(show: true),
                belowBarData: BarAreaData(show: true, color: kBlueLight.withOpacity(0.5)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProchainsCoursCard() {
    final List<dynamic> prochains = _data?['prochains_cours'] ?? [];
    return _card(
      title: 'Prochains cours',
      child: prochains.isEmpty
          ? const Text('Aucune séance à venir programmée.', style: TextStyle(color: kTextMuted, fontSize: 12.5))
          : Column(
              children: prochains.map<Widget>((c) => Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: kBg, borderRadius: BorderRadius.circular(10)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(c['intitule'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 6),
                    Row(children: [
                      const Icon(Icons.access_time_rounded, size: 13, color: kTextMuted),
                      const SizedBox(width: 4),
                      Text('${c['date']} · ${(c['heure_debut'] as String).substring(0,5)}-${(c['heure_fin'] as String).substring(0,5)}',
                          style: const TextStyle(fontSize: 11.5, color: kTextMuted)),
                    ]),
                    const SizedBox(height: 3),
                    Row(children: [
                      const Icon(Icons.location_on_rounded, size: 13, color: kTextMuted),
                      const SizedBox(width: 4),
                      Text('${c['lieu']} · Prof. ${c['enseignant_nom']}', style: const TextStyle(fontSize: 11.5, color: kTextMuted)),
                    ]),
                  ],
                ),
              )).toList(),
            ),
    );
  }

  Widget _buildHistoriqueCard() {
    final List<dynamic> historique = _data?['historique'] ?? [];
    return _card(
      title: 'Historique récent',
      child: historique.isEmpty
          ? const Text('Aucun pointage enregistré pour l\'instant.', style: TextStyle(color: kTextMuted, fontSize: 12.5))
          : Column(
              children: historique.map<Widget>((h) {
                final statut = h['statut'] ?? '';
                final estValide = statut == 'VALIDE';
                final bg = estValide ? kGreenLight : kRedLight;
                final fg = estValide ? kGreen : kRed;
                final label = estValide ? 'Présent' : (statut == 'HORS_ZONE' ? 'Hors zone' : statut);

                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(color: kBg, borderRadius: BorderRadius.circular(10)),
                  child: Row(
                    children: [
                      Icon(estValide ? Icons.check_circle_rounded : Icons.cancel_rounded, color: fg, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(h['cours'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
                            Text('${h['date']} · ${h['lieu'] ?? ''}', style: const TextStyle(fontSize: 11, color: kTextMuted)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(6)),
                        child: Text(label, style: TextStyle(fontSize: 10.5, color: fg, fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
    );
  }
}