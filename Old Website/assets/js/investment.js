// assets/js/investment.js
import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getFirestore, doc, getDoc, setDoc, serverTimestamp, collection, getDocs, deleteDoc, query, orderBy } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged, setPersistence, browserSessionPersistence } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// ==========================================
// FIREBASE CONFIGURATION
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

// Initialize Firebase (reuse existing app if already initialized)
let app, db, auth;
let isFirebaseConfigured = false;

try {
  const existingApps = getApps();
  // Use a named app "investment" to avoid conflicts with training.js
  const investmentAppName = "investment-app";
  const existingInvApp = existingApps.find(a => a.name === investmentAppName);
  if (existingInvApp) {
    app = existingInvApp;
  } else {
    app = initializeApp(firebaseConfig, investmentAppName);
  }
  db = getFirestore(app);
  auth = getAuth(app);
  setPersistence(auth, browserSessionPersistence).catch(err => console.error("Failed to set auth persistence:", err));
  isFirebaseConfigured = true;
} catch (err) {
  console.error("Firebase initialization error:", err);
}

function checkConfiguration() {
  if (!isFirebaseConfigured) {
    alert("Firebase configuration is not set up.");
    return false;
  }
  return true;
}

// ==========================================
// AUTHENTICATION
// ==========================================
export async function loginAdmin(email, password) {
  if (!checkConfiguration()) return null;
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  } catch (error) {
    console.error("Login failed:", error);
    throw error;
  }
}

export async function logoutAdmin() {
  if (!checkConfiguration()) return;
  try {
    await signOut(auth);
  } catch (error) {
    console.error("Logout failed:", error);
    throw error;
  }
}

export function onAdminAuthStateChanged(callback) {
  if (!checkConfiguration()) return;
  onAuthStateChanged(auth, callback);
}

// ==========================================
// HELPER: Sequential ID Generator
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
        if (!isNaN(num) && num > maxNum) maxNum = num;
      }
    });
    return prefix + String(maxNum + 1).padStart(paddingSize, "0");
  } catch (err) {
    console.error("Error generating ID:", err);
    return prefix + "0001";
  }
}

// ==========================================
// INVESTORS (Enrollment / Database)
// ==========================================

export async function addInvestor(investorData) {
  if (!checkConfiguration()) return null;
  const { fullName, email, phone, investorType, nationality, idNumber, riskProfile, notes } = investorData;
  if (!fullName || !email || !phone) throw new Error("Missing required investor fields");

  try {
    const id = await getNextSeqId("inv_investors", "INV-", "investorId");
    const docRef = doc(db, "inv_investors", id);
    await setDoc(docRef, {
      investorId: id,
      fullName: fullName.trim(),
      email: email.trim(),
      phone: phone.trim(),
      investorType: investorType || "Individual",
      nationality: nationality || "",
      idNumber: idNumber || "",
      riskProfile: riskProfile || "Moderate",
      notes: notes || "",
      status: "Active",
      createdAt: serverTimestamp()
    });
    return id;
  } catch (err) {
    console.error("Error adding investor:", err);
    throw err;
  }
}

export async function getAllInvestors() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "inv_investors"));
    const investors = [];
    querySnapshot.forEach(docSnap => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        data.id = docSnap.id;
        investors.push(data);
      }
    });
    return investors;
  } catch (err) {
    console.error("Error fetching investors:", err);
    throw err;
  }
}

export async function updateInvestor(investorId, investorData) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "inv_investors", investorId);
    await setDoc(docRef, { ...investorData, updatedAt: serverTimestamp() }, { merge: true });
  } catch (err) {
    console.error("Error updating investor:", err);
    throw err;
  }
}

export async function deleteInvestor(investorId) {
  if (!checkConfiguration()) return;
  try {
    await deleteDoc(doc(db, "inv_investors", investorId));
  } catch (err) {
    console.error("Error deleting investor:", err);
    throw err;
  }
}

// ==========================================
// INVESTMENTS
// ==========================================

export async function addInvestment(investmentData) {
  if (!checkConfiguration()) return null;
  const { investorId, investorName, investmentType, amount, currency, startDate, maturityDate, returnRate, returnType, status, notes } = investmentData;
  if (!investorId || !amount || !investmentType) throw new Error("Missing required investment fields");

  try {
    const id = await getNextSeqId("inv_investments", "INVT-", "investmentId");
    const docRef = doc(db, "inv_investments", id);
    await setDoc(docRef, {
      investmentId: id,
      investorId: investorId.trim(),
      investorName: investorName || "",
      investmentType: investmentType || "Fixed Deposit",
      amount: Number(amount),
      currency: currency || "BDT",
      startDate: startDate || "",
      maturityDate: maturityDate || "",
      returnRate: Number(returnRate) || 0,
      returnType: returnType || "Annual",
      expectedReturn: calculateExpectedReturn(Number(amount), Number(returnRate), returnType, startDate, maturityDate),
      status: status || "Active",
      notes: notes || "",
      createdAt: serverTimestamp()
    });
    return id;
  } catch (err) {
    console.error("Error adding investment:", err);
    throw err;
  }
}

function calculateExpectedReturn(amount, rate, returnType, startDate, maturityDate) {
  if (!amount || !rate) return 0;
  if (startDate && maturityDate) {
    const start = new Date(startDate);
    const end = new Date(maturityDate);
    const diffMs = end - start;
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    const years = diffDays / 365;
    return Math.round(amount * (rate / 100) * years);
  }
  return Math.round(amount * (rate / 100));
}

export async function getAllInvestments() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "inv_investments"));
    const investments = [];
    querySnapshot.forEach(docSnap => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        data.id = docSnap.id;
        investments.push(data);
      }
    });
    return investments;
  } catch (err) {
    console.error("Error fetching investments:", err);
    throw err;
  }
}

export async function updateInvestment(investmentId, investmentData) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "inv_investments", investmentId);
    await setDoc(docRef, { ...investmentData, updatedAt: serverTimestamp() }, { merge: true });
  } catch (err) {
    console.error("Error updating investment:", err);
    throw err;
  }
}

export async function deleteInvestment(investmentId) {
  if (!checkConfiguration()) return;
  try {
    await deleteDoc(doc(db, "inv_investments", investmentId));
  } catch (err) {
    console.error("Error deleting investment:", err);
    throw err;
  }
}

// ==========================================
// AUDIT LOGS (Investment-specific)
// ==========================================
export async function addAuditLog(logData) {
  if (!checkConfiguration()) return;
  const { user_email, action_type, collection_name, record_id, details } = logData;
  if (!user_email || !action_type || !details) throw new Error("Missing required audit log fields");
  try {
    const id = await getNextSeqId("inv_audit_logs", "ILOG-", "log_id", 5);
    const docRef = doc(db, "inv_audit_logs", id);
    await setDoc(docRef, {
      log_id: id,
      user_email,
      action_type,
      collection_name: collection_name || "N/A",
      record_id: record_id || "N/A",
      details,
      local_time: new Date().toLocaleString(),
      createdAt: serverTimestamp()
    });
    return id;
  } catch (err) {
    console.error("Error saving audit log:", err);
  }
}

export async function getAllAuditLogs() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "inv_audit_logs"));
    const logs = [];
    querySnapshot.forEach(docSnap => {
      if (docSnap.exists()) logs.push(docSnap.data());
    });
    logs.sort((a, b) => b.log_id.localeCompare(a.log_id));
    return logs;
  } catch (err) {
    console.error("Error fetching audit logs:", err);
    return [];
  }
}
