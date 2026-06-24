// assets/js/hr.js
// HR Management Dashboard — Firebase Data Layer
// Collections: hr_employees, hr_attendance, hr_leaves, hr_payroll, hr_roster

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import {
  getFirestore, doc, getDoc, setDoc, deleteDoc,
  collection, getDocs, query, where, serverTimestamp, writeBatch
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import {
  getAuth, signInWithEmailAndPassword, signOut,
  onAuthStateChanged, setPersistence, browserSessionPersistence
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// ==========================================
// FIREBASE CONFIGURATION (shared project)
// ==========================================
const firebaseConfig = {
  apiKey: "AIzaSyBS6t7jjgm8xpw-kfa5hIpJvMJ7vzUdzDQ",
  authDomain: "intrex-digital.firebaseapp.com",
  projectId: "intrex-digital",
  storageBucket: "intrex-digital.firebasestorage.app",
  messagingSenderId: "413262848177",
  appId: "1:413262848177:web:c211866e89a5368b79c290",
  measurementId: "G-XRNSDCPK86"
};

let app, db, auth;
let isFirebaseReady = false;

try {
  app  = initializeApp(firebaseConfig, "hr-app"); // named instance to avoid conflicts
  db   = getFirestore(app);
  auth = getAuth(app);
  setPersistence(auth, browserSessionPersistence).catch(e => console.warn("Auth persistence:", e));
  isFirebaseReady = true;
} catch (err) {
  console.error("Firebase init error:", err);
}

function requireDb() {
  if (!isFirebaseReady) throw new Error("Firebase is not initialized.");
}

function checkConfiguration() {
  return isFirebaseReady;
}

// ==========================================
// UTILITY — Sequential ID generator
// ==========================================
async function getNextId(collectionName, prefix, idField, pad = 3) {
  requireDb();
  const snap = await getDocs(collection(db, collectionName));
  let max = 0;
  snap.forEach(d => {
    const val = d.data()[idField] || "";
    if (val.startsWith(prefix)) {
      const n = parseInt(val.slice(prefix.length), 10);
      if (!isNaN(n) && n > max) max = n;
    }
  });
  return prefix + String(max + 1).padStart(pad, "0");
}

// ==========================================
// AUTH
// ==========================================
export async function hrLogin(email, password) {
  requireDb();
  const cred = await signInWithEmailAndPassword(auth, email, password);
  return cred.user;
}

export async function hrLogout() {
  requireDb();
  await signOut(auth);
}

export function onHrAuthState(cb) {
  if (!isFirebaseReady) return;
  onAuthStateChanged(auth, cb);
}

// ==========================================
// EMPLOYEES  (collection: hr_employees)
// ==========================================
export async function saveEmployee(data) {
  requireDb();

  // Basic validation on critical fields
  if (!data.firstName || !data.lastName || !data.department || !data.position || !data.joiningDate) {
    throw new Error("Missing required employee fields (First Name, Last Name, Department, Position, Joining Date).");
  }

  // Email uniqueness check
  if (data.email) {
    const snap = await getDocs(collection(db, "hr_employees"));
    snap.forEach(d => {
      const row = d.data();
      if (row.email?.toLowerCase() === data.email.toLowerCase() && row.emp_id !== data.emp_id) {
        throw new Error(`Email "${data.email}" is already used by another employee.`);
      }
    });
  }

  const id = data.emp_id || await getNextId("hr_employees", "EMP-495", "emp_id", 3);
  const ref = doc(db, "hr_employees", id);
  
  // Clean up and prepare payload
  const payload = {
    ...data,
    emp_id: id,
    name: `${data.firstName} ${data.lastName}`.trim(),
    updatedAt: serverTimestamp()
  };
  
  if (!data.emp_id) {
    payload.createdAt = serverTimestamp();
  }

  await setDoc(ref, payload, { merge: true });
  return id;
}

export async function getAllEmployees() {
  requireDb();
  const snap = await getDocs(collection(db, "hr_employees"));
  return snap.docs.map(d => d.data());
}

export async function deleteEmployee(empId) {
  requireDb();
  await deleteDoc(doc(db, "hr_employees", empId));
}

// ==========================================
// ATTENDANCE  (collection: hr_attendance)
// Doc ID pattern: {empId}_{YYYY-MM-DD}
// ==========================================
export async function setAttendance(empId, date, status) {
  requireDb();
  const id  = `${empId}_${date}`;
  const ref = doc(db, "hr_attendance", id);
  await setDoc(ref, { empId, date, status, updatedAt: serverTimestamp() });
}

export async function getAttendanceByMonth(year, month) {
  requireDb();
  const prefix = `${year}-${String(month).padStart(2, "0")}`;
  const snap = await getDocs(collection(db, "hr_attendance"));
  return snap.docs
    .map(d => d.data())
    .filter(a => a.date && a.date.startsWith(prefix));
}

// Batch-save an entire month's attendance grid
export async function batchSaveAttendance(records) {
  requireDb();
  const batch = writeBatch(db);
  records.forEach(({ empId, date, status }) => {
    const ref = doc(db, "hr_attendance", `${empId}_${date}`);
    batch.set(ref, { empId, date, status, updatedAt: serverTimestamp() });
  });
  await batch.commit();
}

// ==========================================
// LEAVE MANAGEMENT  (collection: hr_leaves)
// ==========================================
export async function saveLeave(data) {
  requireDb();
  const { id, empId, type, from, to, reason, status } = data;
  if (!empId || !type || !from || !to) throw new Error("Missing required leave fields.");
  if (new Date(to) < new Date(from)) throw new Error("To date must be after From date.");

  const docId = id || await getNextId("hr_leaves", "LV-", "id", 4);
  const ref   = doc(db, "hr_leaves", docId);
  await setDoc(ref, {
    id: docId, empId, type,
    from, to, reason: reason || "",
    status: status || "Pending",
    appliedAt: serverTimestamp(),
    updatedAt: serverTimestamp()
  }, { merge: true });
  return docId;
}

export async function getAllLeaves() {
  requireDb();
  const snap = await getDocs(collection(db, "hr_leaves"));
  return snap.docs.map(d => d.data());
}

export async function updateLeaveStatus(leaveId, status) {
  requireDb();
  const ref = doc(db, "hr_leaves", leaveId);
  await setDoc(ref, { status, updatedAt: serverTimestamp() }, { merge: true });
}

export async function deleteLeave(leaveId) {
  requireDb();
  await deleteDoc(doc(db, "hr_leaves", leaveId));
}

// ==========================================
// PAYROLL  (collection: hr_payroll)
// ==========================================
export async function savePayrollRecords(records) {
  requireDb();
  const batch = writeBatch(db);
  records.forEach(r => {
    const ref = doc(db, "hr_payroll", r.id);
    batch.set(ref, { ...r, savedAt: serverTimestamp() });
  });
  await batch.commit();
}

// Delete all records for a given month/year before re-generating
export async function deletePayrollByMonth(month, year) {
  requireDb();
  const snap = await getDocs(collection(db, "hr_payroll"));
  const batch = writeBatch(db);
  snap.docs.forEach(d => {
    const data = d.data();
    if (data.month === month && data.year === year) batch.delete(d.ref);
  });
  await batch.commit();
}

export async function getAllPayroll() {
  requireDb();
  const snap = await getDocs(collection(db, "hr_payroll"));
  return snap.docs.map(d => d.data());
}

export async function getPayrollByMonth(month, year) {
  requireDb();
  const snap = await getDocs(collection(db, "hr_payroll"));
  return snap.docs
    .map(d => d.data())
    .filter(p => p.month === month && p.year === year);
}

// ==========================================
// DUTY ROSTER  (collection: hr_roster)
// Doc ID pattern: {empId}_{YYYY-MM-DD}
// ==========================================
export async function saveRosterEntry(empId, date, shift) {
  requireDb();
  const id  = `${empId}_${date}`;
  const ref = doc(db, "hr_roster", id);
  await setDoc(ref, { empId, date, shift, updatedAt: serverTimestamp() });
}

export async function batchSaveRoster(entries) {
  requireDb();
  const batch = writeBatch(db);
  entries.forEach(({ empId, date, shift }) => {
    const ref = doc(db, "hr_roster", `${empId}_${date}`);
    batch.set(ref, { empId, date, shift, updatedAt: serverTimestamp() });
  });
  await batch.commit();
}

export async function getRosterByWeek(weekStart) {
  requireDb();
  // weekStart = YYYY-MM-DD (Monday)
  const dates = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    dates.push(d.toISOString().slice(0, 10));
  }
  const snap = await getDocs(collection(db, "hr_roster"));
  return snap.docs
    .map(d => d.data())
    .filter(r => dates.includes(r.date));
}


// ==========================================
// AUDIT LOGS SYSTEM (hr_tbl_audit_logs)
// ==========================================

async function getNextSeqId(collectionName, prefix, idField, paddingSize = 4) {
  if (!checkConfiguration()) return prefix + "0001";
  try {
    const querySnapshot = await getDocs(collection(db, collectionName));
    let maxNum = 0;
    querySnapshot.forEach(docSnap => {
      const data = docSnap.data();
      const val = data[idField];
      if (val && val.startsWith(prefix)) {
        const numPart = val.substring(prefix.length);
        const num = parseInt(numPart, 10);
        if (!isNaN(num) && num > maxNum) {
          maxNum = num;
        }
      }
    });
    const nextNum = maxNum + 1;
    return prefix + String(nextNum).padStart(paddingSize, '0');
  } catch (error) {
    console.error("Error generating next sequence ID for " + collectionName + ":", error);
    return prefix + "0001";
  }
}

export async function addAuditLog(logData) {
  if (!checkConfiguration()) return;
  const { user_email, action_type, collection_name, record_id, details } = logData;
  if (!user_email || !action_type || !details) {
    throw new Error("Missing required audit log fields");
  }
  try {
    const id = await getNextSeqId("hr_tbl_audit_logs", "LOG-", "log_id", 5);
    const docRef = doc(db, "hr_tbl_audit_logs", id);
    await setDoc(docRef, {
      log_id: id,
      user_email: user_email,
      action_type: action_type,
      collection_name: collection_name || "N/A",
      record_id: record_id || "N/A",
      details: details,
      local_time: new Date().toLocaleString(),
      createdAt: serverTimestamp()
    });
    return id;
  } catch (error) {
    console.error("Error saving audit log: ", error);
    throw error;
  }
}

export async function getAllAuditLogs() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    return [
      {
        log_id: "LOG-00001",
        local_time: new Date().toLocaleString(),
        user_email: "hr@intrex-digital.com",
        action_type: "LOGIN",
        collection_name: "N/A",
        record_id: "N/A",
        details: "Mock HR Admin logged in successfully to HR dashboard"
      }
    ];
  }

  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "hr_tbl_audit_logs"));
    const logs = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        logs.push(docSnap.data());
      }
    });
    logs.sort((a, b) => b.log_id.localeCompare(a.log_id));
    return logs;
  } catch (error) {
    console.error("Error fetching audit logs: ", error);
    throw error;
  }
}

// ==========================================
// DEPARTMENTS (collection: hr_departments)
// ==========================================
export async function saveDepartment(data) {
  requireDb();
  if (!data.name || !data.status) {
    throw new Error("Missing required department fields (Name, Status).");
  }
  const id = data.id || await getNextId("hr_departments", "DEPT-", "id", 4);
  const ref = doc(db, "hr_departments", id);
  const payload = {
    ...data,
    id: id,
    updatedAt: serverTimestamp()
  };
  if (!data.id) {
    payload.createdAt = serverTimestamp();
  }
  await setDoc(ref, payload, { merge: true });
  return id;
}

export async function getAllDepartments() {
  requireDb();
  const snap = await getDocs(collection(db, "hr_departments"));
  const list = snap.docs.map(d => d.data());
  list.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  return list;
}

export async function deleteDepartment(id) {
  requireDb();
  await deleteDoc(doc(db, "hr_departments", id));
}

// ==========================================
// SUB DEPARTMENTS (collection: hr_subdepartments)
// ==========================================
export async function saveSubDepartment(data) {
  requireDb();
  if (!data.name || !data.parentDept || !data.status) {
    throw new Error("Missing required sub-department fields (Name, Parent Department, Status).");
  }
  const id = data.id || await getNextId("hr_subdepartments", "SDEP-", "id", 4);
  const ref = doc(db, "hr_subdepartments", id);
  const payload = {
    ...data,
    id: id,
    updatedAt: serverTimestamp()
  };
  if (!data.id) {
    payload.createdAt = serverTimestamp();
  }
  await setDoc(ref, payload, { merge: true });
  return id;
}

export async function getAllSubDepartments() {
  requireDb();
  const snap = await getDocs(collection(db, "hr_subdepartments"));
  const list = snap.docs.map(d => d.data());
  list.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  return list;
}

export async function deleteSubDepartment(id) {
  requireDb();
  await deleteDoc(doc(db, "hr_subdepartments", id));
}

// ==========================================
// POSITIONS / DESIGNATIONS (collection: hr_positions)
// ==========================================
export async function savePosition(data) {
  requireDb();
  if (!data.title || !data.department || !data.subDepartment || !data.status) {
    throw new Error("Missing required position fields (Title, Department, Sub Department, Status).");
  }
  const id = data.id || await getNextId("hr_positions", "POS-", "id", 4);
  const ref = doc(db, "hr_positions", id);
  const payload = {
    ...data,
    id: id,
    updatedAt: serverTimestamp()
  };
  if (!data.id) {
    payload.createdAt = serverTimestamp();
  }
  await setDoc(ref, payload, { merge: true });
  return id;
}

export async function getAllPositions() {
  requireDb();
  const snap = await getDocs(collection(db, "hr_positions"));
  const list = snap.docs.map(d => d.data());
  list.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
  return list;
}

export async function deletePosition(id) {
  requireDb();
  await deleteDoc(doc(db, "hr_positions", id));
}
