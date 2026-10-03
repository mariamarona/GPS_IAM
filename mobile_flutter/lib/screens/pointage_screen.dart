import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:shared_preferences/shared_preferences.dart';

const String BASE_URL = 'http://192.168.1.99:8000';

// Cas d'utilisation "Répondre aux contrôles périodiques" : une fois le pointage
// initial validé, l'application redemande la position toutes les X minutes pour
// vérifier que l'étudiant est resté dans la zone (et pas seulement au moment de
// pointer). 15 minutes est la valeur réelle ; réduire temporairement à
// Duration(seconds: 30) est utile pour démontrer la fonctionnalité en soutenance.
const Duration kIntervalleControlePeriodique = Duration(minutes: 15);

class PointageScreen extends StatefulWidget {
  const PointageScreen({super.key});

  @override
  State<PointageScreen> createState() => _PointageScreenState();
}

class _PointageScreenState extends State<PointageScreen>
    with SingleTickerProviderStateMixin {
  // Palette du "panneau GPS" (zone d'action, volontairement sombre — comme un
  // bloc mis en avant, cohérent avec le radar animé) :
  static const Color kBg = Color(0xFF0F172A);
  static const Color kPanel = Color(0xFF122433);
  static const Color kPanelSoft = Color(0xFF172C3D);
  static const Color kGreen = Color(0xFF16A34A);   // réservé au VRAI succès (pointage validé)
  static const Color kRed = Color(0xFFDC2626);
  static const Color kMuted = Color(0xFF7C8CA3);
  static const Color kBlue = Color(0xFF2563EB);    // sélection / action à faire

  // Palette de la page (alignée sur le tableau de bord — fond clair) :
  static const Color kPageBg    = Color(0xFFF5F6F9);
  static const Color kCardLight = Color(0xFFFFFFFF);
  static const Color kBorderLight = Color(0xFFE7E9EE);
  static const Color kTextDark  = Color(0xFF111827);

  late final AnimationController _radarCtrl;

  List<dynamic> _sessions = [];
  dynamic _sessionSelectionnee;
  Position? _positionActuelle;
  bool _isLoadingSessions = true;
  bool _isLocating = false;
  bool _isPointing = false;
  String? _messageResultat;
  bool? _pointageValide;
  String _userId = '';
  Map<String, dynamic>? _dernierResultat;
  String? _heurePointage;

  // ── Contrôles périodiques ──────────────────────────────────
  Timer? _controleTimer;
  DateTime? _prochainControleA;
  bool _controleEnCours = false;

  @override
  void initState() {
    super.initState();
    _radarCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
    _loadUserId();
    _loadSessions();
  }

  @override
  void dispose() {
    _radarCtrl.dispose();
    _controleTimer?.cancel();
    super.dispose();
  }

  /// Récupère la position GPS sans toucher aux états visuels du bouton de
  /// pointage principal (utilisée par les contrôles périodiques, en tâche de fond).
  Future<Position?> _obtenirPositionSilencieuse() async {
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return null;
      }
      return await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
    } catch (_) {
      return null;
    }
  }

  /// Démarre les contrôles périodiques après un pointage initial validé.
  void _demarrerControlesPeriodiques(int pointageId) {
    _controleTimer?.cancel();
    setState(() {
      _prochainControleA = DateTime.now().add(kIntervalleControlePeriodique);
    });
    _controleTimer = Timer.periodic(kIntervalleControlePeriodique, (_) {
      _declencherControle(pointageId);
    });
  }

  /// Affiche la demande de contrôle et laisse l'étudiant confirmer sa position.
  Future<void> _declencherControle(int pointageId) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Contrôle périodique GPS'),
          content: const Text(
            "Confirmez votre position pour rester marqué présent à cette séance.",
          ),
          actions: [
            TextButton(
              onPressed: _controleEnCours
                  ? null
                  : () async {
                      Navigator.of(dialogContext).pop();
                      await _repondreControle(pointageId);
                    },
              child: const Text('Confirmer ma position'),
            ),
          ],
        );
      },
    );
  }

  /// Envoie la position au serveur pour un contrôle périodique donné, puis
  /// programme le contrôle suivant (que la réponse soit valide ou non).
  Future<void> _repondreControle(int pointageId) async {
    setState(() => _controleEnCours = true);
    final position = await _obtenirPositionSilencieuse();
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token') ?? '';

    if (position == null) {
      setState(() => _controleEnCours = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Impossible de récupérer votre position GPS.')),
        );
      }
      _demarrerControlesPeriodiques(pointageId); // on réessaiera au prochain intervalle
      return;
    }

    try {
      final res = await http.post(
        Uri.parse('$BASE_URL/api/pointages/$pointageId/controle-periodique/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'latitude': position.latitude,
          'longitude': position.longitude,
        }),
      );
      final data = jsonDecode(res.body);
      final dansZone = data['dans_zone'] == true;

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: dansZone ? kGreen : kRed,
            content: Text(
              dansZone
                  ? '✅ Position confirmée.'
                  : "⚠️ Vous n'êtes plus dans la zone autorisée — une alerte a été enregistrée.",
            ),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Impossible de contacter le serveur pour le contrôle.')),
        );
      }
    } finally {
      setState(() => _controleEnCours = false);
      // La séance continue : on programme le contrôle suivant tant que l'écran est ouvert.
      _demarrerControlesPeriodiques(pointageId);
    }
  }

  Future<void> _loadUserId() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() => _userId = prefs.getString('user_id') ?? '');
  }

  Future<void> _loadSessions() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token') ?? '';

    setState(() => _isLoadingSessions = true);

    try {
      final res = await http.get(
        Uri.parse('$BASE_URL/api/sessions/aujourd-hui/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final sessions = (data['sessions'] as List)
            .where(
                (s) => s['statut'] == 'EN_COURS' || s['statut'] == 'PLANIFIE')
            .toList();

        setState(() {
          _sessions = sessions;
          _sessionSelectionnee = sessions.isNotEmpty ? sessions.first : null;
          _isLoadingSessions = false;
        });
      } else {
        setState(() => _isLoadingSessions = false);
      }
    } catch (_) {
      setState(() {
        _messageResultat = 'Impossible de charger les sessions du jour.';
        _pointageValide = false;
        _isLoadingSessions = false;
      });
    }
  }

  Future<Position?> _obtenirPosition() async {
    setState(() {
      _isLocating = true;
      _messageResultat = null;
      _pointageValide = null;
    });

    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied) {
        setState(() {
          _messageResultat = 'Permission de localisation refusee.';
          _pointageValide = false;
          _isLocating = false;
        });
        return null;
      }

      if (permission == LocationPermission.deniedForever) {
        setState(() {
          _messageResultat = 'Activez la localisation dans les parametres.';
          _pointageValide = false;
          _isLocating = false;
        });
        return null;
      }

      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      setState(() {
        _positionActuelle = position;
        _isLocating = false;
      });
      return position;
    } catch (_) {
      setState(() {
        _messageResultat = 'Erreur pendant la localisation GPS.';
        _pointageValide = false;
        _isLocating = false;
      });
      return null;
    }
  }

  Future<void> _pointerMaintenant() async {
    if (_sessionSelectionnee == null) {
      setState(() {
        _messageResultat = 'Aucune session disponible aujourd hui.';
        _pointageValide = false;
      });
      return;
    }

    final position = await _obtenirPosition();
    if (position == null) return;

    setState(() {
      _isPointing = true;
      _messageResultat = 'Analyse IA en cours...';
    });

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token') ?? '';

    try {
      // Heure exacte de l'appareil au moment du pointage — envoyée au serveur
      // pour que l'heure enregistrée et affichée corresponde toujours à celle
      // du téléphone de l'étudiant, et non à l'horloge du serveur.
      final heureAppareil = DateTime.now();

      final res = await http.post(
        Uri.parse('$BASE_URL/api/pointages/valider/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'utilisateur_id': _userId,
          'session_id': _sessionSelectionnee['id'],
          'latitude': position.latitude,
          'longitude': position.longitude,
          'precision_gps_m': position.accuracy,
          'timestamp_appareil': heureAppareil.toIso8601String(),
        }),
      );

      final data = jsonDecode(res.body);

      if (res.statusCode == 201) {
        final dansZone = data['dans_zone'] == true;
        final hh = heureAppareil.hour.toString().padLeft(2, '0');
        final mm = heureAppareil.minute.toString().padLeft(2, '0');
        final ss = heureAppareil.second.toString().padLeft(2, '0');
        setState(() {
          _pointageValide = dansZone;
          _messageResultat =
              dansZone ? 'Position dans la zone' : 'Position hors zone';
          _dernierResultat = data;
          _heurePointage = (data['heure_pointage'] as String?) ?? '$hh:$mm:$ss';
        });
        // Cas d'utilisation "Répondre aux contrôles périodiques" : une fois le
        // pointage initial validé (dans la zone), on démarre les vérifications
        // périodiques de position pour le reste de la séance.
        if (dansZone && data['pointage_id'] != null) {
          _demarrerControlesPeriodiques(data['pointage_id'] as int);
        }
      } else {
        setState(() {
          _pointageValide = false;
          _messageResultat = data['error'] ?? 'Erreur lors du pointage.';
        });
      }
    } catch (_) {
      setState(() {
        _pointageValide = false;
        _messageResultat = 'Impossible de contacter le serveur.';
      });
    } finally {
      setState(() => _isPointing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sessionTitle = _sessionSelectionnee?['intitule'] ??
        _sessionSelectionnee?['module'] ??
        'Pointage GPS';
    final sessionPlace = _sessionSelectionnee?['zone'] ?? 'Zone de presence';
    final statusColor = _pointageValide == false
        ? kRed
        : _pointageValide == true
            ? kGreen
            : kBlue; // état neutre / avant toute vérification — jamais vert par défaut

    return Scaffold(
      backgroundColor: kPageBg,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadSessions,
          color: kBlue,
          backgroundColor: kCardLight,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildTopBar(),
                const SizedBox(height: 28),
                Text(
                  'Pointage GPS',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: kTextDark,
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  '$sessionTitle\n$sessionPlace',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: kMuted,
                    fontSize: 13,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 24),
                _buildGpsPanel(statusColor),
                const SizedBox(height: 18),
                _buildSessionSelector(),
                const SizedBox(height: 18),
                _buildZoneMap(),
                const SizedBox(height: 18),
                _buildDetailsPanel(),
                if (_prochainControleA != null) ...[
                  const SizedBox(height: 18),
                  _buildControlePeriodiqueIndicator(),
                ],
                const SizedBox(height: 20),
                _buildPointageButton(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Row(
      children: [
        IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_rounded, color: kTextDark),
          style: IconButton.styleFrom(
            backgroundColor: kBorderLight,
          ),
        ),
        const Spacer(),
        Row(
          children: [
            Container(
              width: 7,
              height: 7,
              decoration: const BoxDecoration(
                color: kGreen,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            const Text(
              'GPS actif',
              style: TextStyle(
                color: kGreen,
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildGpsPanel(Color statusColor) {
    return Container(
      height: 276,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: kPanel,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: statusColor.withOpacity(0.35), width: 1.4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.22),
            blurRadius: 24,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        children: [
          Expanded(
            child: AnimatedBuilder(
              animation: _radarCtrl,
              builder: (_, __) {
                return CustomPaint(
                  painter: _RadarPainter(
                    progress: _radarCtrl.value,
                    color: statusColor,
                    isActive: _isLocating || _isPointing,
                  ),
                  child: Center(
                    child: Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.95),
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: statusColor.withOpacity(0.28),
                            blurRadius: 18,
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                      alignment: Alignment.center,
                      child: const Text(
                        'GPS',
                        style: TextStyle(
                          color: kBg,
                          fontSize: 11,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 12),
          Text(
            _statusTitle(),
            textAlign: TextAlign.center,
            style: TextStyle(
              color: statusColor,
              fontSize: 16,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            _isPointing
                ? 'Analyse IA en cours...'
                : _isLocating
                    ? 'Localisation GPS en cours...'
                    : _statusSubtitle(),
            textAlign: TextAlign.center,
            style: const TextStyle(color: kMuted, fontSize: 12),
          ),
        ],
      ),
    );
  }

  String _statusTitle() {
    if (_isLocating) return 'Recherche de position';
    if (_isPointing) return 'Verification en cours';
    if (_pointageValide == true) return 'Position dans la zone';
    if (_pointageValide == false) return 'Alerte de position';
    return 'Pret pour le pointage';
  }

  String _statusSubtitle() {
    if (_dernierResultat != null) {
      return 'Distance: ${_dernierResultat!['distance_m']}m / ${_dernierResultat!['rayon_zone_m']}m autorises';
    }
    return 'Selectionnez une session puis lancez le pointage';
  }

  Widget _buildSessionSelector() {
    if (_isLoadingSessions) {
      return const Center(child: CircularProgressIndicator(color: kGreen));
    }

    if (_sessions.isEmpty) {
      return _buildInfoTile(
        icon: Icons.event_busy_rounded,
        title: 'Aucune session disponible',
        subtitle: 'Demandez a l enseignant de demarrer une session.',
        color: kRed,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Seances du jour',
          style: TextStyle(
            color: kMuted,
            fontSize: 12,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 10),
        ..._sessions.map((session) {
          final selected = _sessionSelectionnee?['id'] == session['id'];
          return GestureDetector(
            onTap: () => setState(() {
              _sessionSelectionnee = session;
              _messageResultat = null;
              _pointageValide = null;
              _dernierResultat = null;
            }),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: selected ? kBlue.withOpacity(0.06) : kCardLight,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: selected ? kBlue.withOpacity(0.4) : kBorderLight,
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: selected
                          ? kBlue.withOpacity(0.12)
                          : kBorderLight,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      // Cette icône indique juste la séance SÉLECTIONNÉE — pas un pointage déjà
                      // effectué (aucune coche verte ici, pour ne pas induire en erreur).
                      selected
                          ? Icons.radio_button_checked_rounded
                          : Icons.radio_button_unchecked_rounded,
                      color: selected ? kBlue : kMuted,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          session['intitule'] ?? session['module'] ?? '',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: kTextDark,
                            fontWeight: FontWeight.w800,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${session['heure_debut']} - ${session['heure_fin']} · ${session['zone']}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: kMuted, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      color: kBlue,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      'Pointer',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget _buildZoneMap() {
    final zoneDetail = _sessionSelectionnee?['zone_detail'];
    if (zoneDetail == null) {
      return const SizedBox.shrink();
    }

    final zoneLat = double.tryParse('${zoneDetail['latitude']}');
    final zoneLng = double.tryParse('${zoneDetail['longitude']}');
    if (zoneLat == null || zoneLng == null) {
      return const SizedBox.shrink();
    }

    final rayonM = (zoneDetail['rayon_m'] is num)
        ? (zoneDetail['rayon_m'] as num).toDouble()
        : double.tryParse('${zoneDetail['rayon_m']}') ?? 50.0;

    final zoneCenter = LatLng(zoneLat, zoneLng);
    final maPosition = _positionActuelle != null
        ? LatLng(_positionActuelle!.latitude, _positionActuelle!.longitude)
        : null;

    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: Container(
        height: 220,
        decoration: BoxDecoration(
          border: Border.all(color: kBorderLight),
        ),
        child: Stack(
          children: [
            FlutterMap(
              options: MapOptions(
                initialCenter: zoneCenter,
                initialZoom: 17,
                interactionOptions: const InteractionOptions(
                  flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag,
                ),
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.iamgps.app',
                ),
                CircleLayer(
                  circles: [
                    CircleMarker(
                      point: zoneCenter,
                      radius: rayonM,
                      useRadiusInMeter: true,
                      color: kGreen.withOpacity(0.15),
                      borderColor: kGreen,
                      borderStrokeWidth: 2,
                    ),
                  ],
                ),
                MarkerLayer(
                  markers: [
                    Marker(
                      point: zoneCenter,
                      width: 34,
                      height: 34,
                      child: const Icon(Icons.school_rounded, color: kGreen, size: 30),
                    ),
                    if (maPosition != null)
                      Marker(
                        point: maPosition,
                        width: 26,
                        height: 26,
                        child: Container(
                          decoration: BoxDecoration(
                            color: (_pointageValide == false) ? kRed : Colors.blueAccent,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 2.5),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.3),
                                blurRadius: 6,
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ],
            ),
            Positioned(
              left: 10,
              bottom: 10,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.55),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  '© OpenStreetMap',
                  style: TextStyle(color: Colors.white70, fontSize: 9),
                ),
              ),
            ),
            Positioned(
              right: 10,
              top: 10,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: kPanel.withOpacity(0.9),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.white10),
                ),
                child: Text(
                  zoneDetail['nom'] ?? 'Zone IAM',
                  style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailsPanel() {
    if (_messageResultat == null && _positionActuelle == null) {
      return _buildInfoTile(
        icon: Icons.shield_outlined,
        title: 'Controle GPS et IA',
        subtitle: 'La position, la precision et la zone seront verifiees.',
        color: kBlue,
      );
    }

    final sousDetails = <String>[];
    if (_positionActuelle != null) {
      sousDetails.add('Precision GPS: ${_positionActuelle!.accuracy.toStringAsFixed(1)}m');
    }
    if (_heurePointage != null) {
      sousDetails.add('Pointé à $_heurePointage');
    }

    return _buildInfoTile(
      icon: _pointageValide == false
          ? Icons.warning_amber_rounded
          : Icons.verified_rounded,
      title: _messageResultat ?? 'Position obtenue',
      subtitle: sousDetails.isEmpty
          ? 'En attente de localisation.'
          : sousDetails.join(' · '),
      color: _pointageValide == false ? kRed : kGreen,
    );
  }

  // Cas d'utilisation "Répondre aux contrôles périodiques" : indique à
  // l'étudiant (et au jury pendant la soutenance) que la vérification GPS
  // périodique est active pendant le reste de la séance.
  Widget _buildControlePeriodiqueIndicator() {
    final heure = _prochainControleA!;
    final hh = heure.hour.toString().padLeft(2, '0');
    final mm = heure.minute.toString().padLeft(2, '0');
    return _buildInfoTile(
      icon: _controleEnCours ? Icons.gps_fixed : Icons.timer_outlined,
      title: _controleEnCours
          ? 'Contrôle périodique en cours...'
          : 'Contrôle périodique actif',
      subtitle: _controleEnCours
          ? 'Vérification de votre position en cours.'
          : 'Prochaine vérification vers $hh:$mm',
      color: kBlue,
    );
  }

  Widget _buildInfoTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: kCardLight,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: kBorderLight),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: color.withOpacity(0.14),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: kTextDark,
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(color: kMuted, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPointageButton() {
    final disabled = _isPointing ||
        _isLocating ||
        _isLoadingSessions ||
        _sessionSelectionnee == null;

    return SizedBox(
      height: 54,
      child: ElevatedButton.icon(
        onPressed: disabled ? null : _pointerMaintenant,
        icon: (_isPointing || _isLocating)
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : const Icon(Icons.fingerprint_rounded),
        label: Text(
          _isPointing
              ? 'Analyse en cours...'
              : _isLocating
                  ? 'Localisation...'
                  : 'Pointer maintenant',
          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: kGreen,
          disabledBackgroundColor: kGreen.withOpacity(0.45),
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
    );
  }
}

class _RadarPainter extends CustomPainter {
  const _RadarPainter({
    required this.progress,
    required this.color,
    required this.isActive,
  });

  final double progress;
  final Color color;
  final bool isActive;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) * 0.36;
    final ringPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..color = color.withOpacity(0.14);

    for (var i = 1; i <= 4; i++) {
      canvas.drawCircle(center, radius * i / 4, ringPaint);
    }

    final mainRing = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6
      ..color = color.withOpacity(0.65);
    canvas.drawCircle(center, radius * 0.52, mainRing);

    final sweepPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        startAngle: 0,
        endAngle: math.pi * 2,
        colors: [
          color.withOpacity(0),
          color.withOpacity(isActive ? 0.25 : 0.12),
          color,
        ],
        stops: const [0.0, 0.72, 1.0],
        transform: GradientRotation(progress * math.pi * 2),
      ).createShader(Rect.fromCircle(center: center, radius: radius));

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius * 0.88),
      -math.pi / 2,
      math.pi * 0.9,
      false,
      sweepPaint,
    );

    final glowPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = color.withOpacity(isActive ? 0.07 : 0.04);
    canvas.drawCircle(center, radius * (0.72 + progress * 0.18), glowPaint);
  }

  @override
  bool shouldRepaint(covariant _RadarPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.color != color ||
        oldDelegate.isActive != isActive;
  }
}