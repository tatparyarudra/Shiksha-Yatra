import 'package:flutter/material.dart';

class AdminDashboardScreen extends StatelessWidget {
  const AdminDashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Administrator Portal'),
        backgroundColor: Colors.green[600],
      ),
      body: const Center(
        child: Text('Admin Portal Under Construction', style: TextStyle(fontSize: 20)),
      ),
    );
  }
}
