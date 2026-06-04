# DAFI-project
Sistem Cyber-Fizic pentru Monitorizare AMR Pharma

# README – Proiect DAFI: AMR Pharma (Sistem Cyber-Fizic GxP)

**Disciplina:** Dezvoltarea Arhitecturilor de Fabricare Inteligente (DAFI)  
**Instituție:** Universitatea POLITEHNICA București – FIIR  
**Student:** Ana-Maria MIU (Master AIII)  
**Data:** Mai 2026  

---

## Ce face acest proiect?
  Acest proiect reprezintă prototipul software pentru un **Sistem Ciber-Fizic (CPS)** de nivel industrial. Simulează un robot autonom (AMR) dotat cu un senzor pe un braț telescopic, care se plimbă printre rafturile unui depozit farmaceutic (High-Bay) pentru a verifica dacă medicamentele sunt păstrate în condiții optime (sub 25°C), mapând totul în format 3D.

  Sistemul este împărțit în două module decuplate care comunică prin internet (MQTT):
    1. **Creierul Robotului (`engine.py`):** Rulează fizic pe robot (Edge). Controlează hardware-ul, scanează temperatura la 3 înălțimi diferite, supraveghează bateria și loghează automat fiecare mișcare într-un registru intern imuabil (baza de date SQLite).
    2. **Interfața Web / Digital Twin (`app.py`):** Rulează pe PC-ul managerului. Oferă o hartă termică volumetrică 3D în timp real, panou de comandă și generare de rapoarte de audit.

---

## Conturi de Utilizator (RBAC - Role-Based Access Control)
  Sistemul implementează securitate strictă. În funcție de rol, utilizatorii au permisiuni diferite pentru a garanta integritatea datelor (Segregation of Duties):

| Utilizator | Parolă | Rol și Nivel de Acces |
| :--- | :--- | :--- |
| **`manager`** | `dafi2026` | **Control Operațional (Read & Write):** Poate porni misiunea (START), poate seta dimensiunile halei și poate opri de urgență robotul. |
| **`auditor`** | `pharma123` | **Inspector Calitate (Read-Only):** Acces dedicat exclusiv vizualizării hărții și descărcării rapoartelor de deviații GxP (.XLSX) și tehnice (.CSV). Butoanele de control robot sunt blocate. |

---

## 1. Tabelul Nevoie Reală → Soluție CPS → Modul Software

| *Nevoie reală concretă* | *Cum o rezolvă CPS-ul propus* | *Modul software responsabil* |
|:---|:---|:---|
| **Monitorizarea zonelor oarbe în rafturi High-Bay** | Deplasare X,Y și scanare secvențială la 3 înălțimi (Z) via braț telescopic | Starea `SCAN_HEIGHTS` din `engine.py` |
| **Menținerea integrității medicamentelor (GDP)** | Detectarea excursiilor termice (> 25°C) în timp real și afișarea în Harta 3D | HMI Dashboard (`app.py`) |
| **Garantarea datelor pentru audit farmaceutic** | Logare digitală securizată ALCOA+ în SQLite a *fiecărei stări FSM*, rezistentă la căderi Wi-Fi | Continuous Edge Logging (`engine.py`) |

---

## 2. Diagrama State Machine a Sistemului (Automatul de Stări)

  Robotul împarte misiunea în pași discreți și deterministici. O noutate față de simulările clasice este prezența stării de `INIT`, care reprezintă calibrarea hardware reală înainte de acceptarea comenzilor.

### Reprezentare Vizuală (Sintaxă Mermaid)

```mermaid
stateDiagram-v2
    direction TB
    
    state "Inițializare Hardware (INIT)" as INIT
    state "Așteptare Misiune (IDLE)" as IDLE
    state "Deplasare la Coloană (NAVIGATE)" as NAVIGATE
    state "Scanare 3 Înălțimi (SCAN_HEIGHTS)" as SCAN_HEIGHTS
    state "Salvare & Sincronizare DB (EDGE_SAVE_AND_SYNC)" as EDGE_SAVE_AND_SYNC
    state "Oprire Siguranță & Încărcare (SAFE_STOP)" as SAFE_STOP
    
    [*] --> INIT : Pornire fizică sistem (Alimentare)
    
    INIT --> IDLE : Auto-diagnostic OK (Senzori & LiDAR)
    IDLE --> NAVIGATE : Primire comandă START (MQTT)
    
    %% Fluxul normal de operare
    NAVIGATE --> SCAN_HEIGHTS : Ajuns la poziție (Baterie > 15%)
    SCAN_HEIGHTS --> EDGE_SAVE_AND_SYNC : Scanare Z completă (0.2m, 1.5m, 3.0m)
    
    %% Deciziile după salvarea datelor
    EDGE_SAVE_AND_SYNC --> NAVIGATE : Continuare misiune (Următorul punct X, Y)
    EDGE_SAVE_AND_SYNC --> IDLE : Misiune completă (S-a depășit Y max)
    
    %% Tranzițiile de siguranță pentru baterie scăzută
    NAVIGATE --> SAFE_STOP : Baterie <= 15%
    EDGE_SAVE_AND_SYNC --> SAFE_STOP : Baterie <= 15%
    
    %% Ciclul de reîncărcare
    SAFE_STOP --> IDLE : Baterie încărcată (100%)
    
    %% Întreruperea manuală (Butonul STOP din interfață)
    NAVIGATE --> IDLE : Apăsare Buton STOP
    SCAN_HEIGHTS --> IDLE : Apăsare Buton STOP
    EDGE_SAVE_AND_SYNC --> IDLE : Apăsare Buton STOP

## 3. Justificarea State Machine-ului (Orientare Industrială)
  - Tranziția Hardware (INIT → IDLE): Un robot nu pornește direct gata de misiune. Starea INIT blochează sistemul timp de 4 secunde pentru calibrarea senzorilor și citirea tensiunii bateriei, prevenind pornirile accidentale sau erorile de senzori reci.
  - Eficientizare Hardware: Robotul separă complet starea de deplasare de starea de achiziție (SCAN_HEIGHTS). Robotul se oprește complet la fiecare coloană înainte de a ridica senzorul, eliminând vibrațiile mecanice care ar putea altera citirea termică.
  - Integritatea Datelor (ALCOA+): Robotul trece în salvare (EDGE_SAVE_AND_SYNC) doar după ce a generat pachetul complet de la toate cele 3 cote Z, eliminând riscul raportării unor profile termice trunchiate.
  - Siguranță Industrială (Fault-Tolerant): Dacă bateria atinge 15%, robotul declanșează prioritar SAFE_STOP, abandonând traseul pentru a se reîncărca. Această stare previne moartea subită a robotului pe coridoare.

## Limite din Realitatea Industrială (Considerente Hardware)
  - Acest prototip rezolvă provocări majore care apar într-o hală reală, depășind o simplă simulare:
  - Dinamica Brațului Telescopic: În simulare, scanarea se face rapid. În realitate, extinderea unui catarg la 3 metri induce vibrații. Starea SCAN_HEIGHTS simulează un "timp de stabilizare" de câteva secunde necesar senzorului pentru a nu raporta curenții de aer drept fluctuații de temperatură.
  - Efectul Cuștii Faraday: Rafturile metalice masive blochează frecvent semnalul Wi-Fi. De aceea, arhitectura a fost dotată cu Edge Data Logging: datele sunt scrise local în SQLite pe robot, fiind imune la căderile de internet, salvând integritatea auditului.

## Ghid de Instalare și Rulare (Pentru Utilizatori)
  - Pentru ca sistemul să funcționeze corect, Microserviciile trebuie pornite secvențial, în două terminale separate.

### Pasul 0: Cerințe preliminare
  - Asigură-te că ai Python instalat și instalează pachetele rulând în terminal:
  pip install dash pandas plotly paho-mqtt

### Pasul 1: Pornește "Creierul" Robotului (Edge FSM)
  - Deschide primul terminal în folderul proiectului și rulează:
  python engine.py
  (Așteaptă ca sistemul să facă auto-diagnosticul INIT și să afișeze că a trecut în starea IDLE. Lasă acest terminal deschis în fundal).

### Pasul 2: Pornește Interfața Web (Digital Twin)
  - Păstrând primul terminal deschis, deschide un al doilea terminal nou și rulează:
  python app.py

Pasul 3: Accesarea Sistemului
  - Deschide un browser și navighează la: http://127.0.0.1:8050
  - Loghează-te folosind contul: manager (Parolă: dafi2026).
  - Setează dimensiunea halei (ex: 10x10) și apasă butonul START MISSION. Urmărește cum se populează harta termică 3D în timp real pe măsură ce robotul transmite date!
