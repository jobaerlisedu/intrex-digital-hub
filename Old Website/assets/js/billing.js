// assets/js/billing.js
import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getFirestore, doc, getDoc, setDoc, serverTimestamp, collection, getDocs, deleteDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
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
  const billingAppName = "billing-app";
  const existingBillingApp = existingApps.find(a => a.name === billingAppName);
  if (existingBillingApp) {
    app = existingBillingApp;
  } else {
    app = initializeApp(firebaseConfig, billingAppName);
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
// CLIENTS (billing_clients)
// ==========================================
export async function addClient(clientData) {
  if (!checkConfiguration()) return null;
  const { name, contactPerson, email, phone, address, notes } = clientData;
  if (!name || !email || !phone) throw new Error("Missing required client fields");

  try {
    const id = await getNextSeqId("billing_clients", "BCL-", "clientId", 3);
    const docRef = doc(db, "billing_clients", id);
    await setDoc(docRef, {
      clientId: id,
      name: name.trim(),
      contactPerson: contactPerson || "",
      email: email.trim(),
      phone: phone.trim(),
      address: address || "",
      notes: notes || "",
      status: "Active",
      createdAt: serverTimestamp()
    });
    return id;
  } catch (err) {
    console.error("Error adding client:", err);
    throw err;
  }
}

export async function getAllClients() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "billing_clients"));
    const clients = [];
    querySnapshot.forEach(docSnap => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        data.id = docSnap.id;
        clients.push(data);
      }
    });
    return clients;
  } catch (err) {
    console.error("Error fetching clients:", err);
    throw err;
  }
}

export async function updateClient(clientId, clientData) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "billing_clients", clientId);
    await setDoc(docRef, { ...clientData, updatedAt: serverTimestamp() }, { merge: true });
  } catch (err) {
    console.error("Error updating client:", err);
    throw err;
  }
}

export async function deleteClient(clientId) {
  if (!checkConfiguration()) return;
  try {
    await deleteDoc(doc(db, "billing_clients", clientId));
  } catch (err) {
    console.error("Error deleting client:", err);
    throw err;
  }
}

// ==========================================
// INVOICES (billing_invoices)
// ==========================================
export async function addInvoice(invoiceData) {
  if (!checkConfiguration()) return null;
  const { clientId, clientName, clientEmail, invoiceDate, dueDate, items, subtotal, taxRate, taxAmount, discountAmount, totalAmount, status, paymentMethod, paidDate, notes } = invoiceData;
  if (!clientId || !invoiceDate || !dueDate || !items || items.length === 0) throw new Error("Missing required invoice fields");

  try {
    const id = await getNextSeqId("billing_invoices", "BINV-", "invoiceId", 4);
    const docRef = doc(db, "billing_invoices", id);
    await setDoc(docRef, {
      invoiceId: id,
      clientId: clientId.trim(),
      clientName: clientName || "",
      clientEmail: clientEmail || "",
      invoiceDate: invoiceDate || "",
      dueDate: dueDate || "",
      items: items || [],
      subtotal: Number(subtotal) || 0,
      taxRate: Number(taxRate) || 0,
      taxAmount: Number(taxAmount) || 0,
      discountAmount: Number(discountAmount) || 0,
      totalAmount: Number(totalAmount) || 0,
      status: status || "Unpaid",
      paymentMethod: paymentMethod || "Bank Transfer",
      paidDate: paidDate || "",
      notes: notes || "",
      createdAt: serverTimestamp()
    });
    return id;
  } catch (err) {
    console.error("Error adding invoice:", err);
    throw err;
  }
}

export async function getAllInvoices() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "billing_invoices"));
    const invoices = [];
    querySnapshot.forEach(docSnap => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        data.id = docSnap.id;
        invoices.push(data);
      }
    });
    return invoices;
  } catch (err) {
    console.error("Error fetching invoices:", err);
    throw err;
  }
}

export async function updateInvoice(invoiceId, invoiceData) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "billing_invoices", invoiceId);
    await setDoc(docRef, { ...invoiceData, updatedAt: serverTimestamp() }, { merge: true });
  } catch (err) {
    console.error("Error updating invoice:", err);
    throw err;
  }
}

export async function deleteInvoice(invoiceId) {
  if (!checkConfiguration()) return;
  try {
    await deleteDoc(doc(db, "billing_invoices", invoiceId));
  } catch (err) {
    console.error("Error deleting invoice:", err);
    throw err;
  }
}

// ==========================================
// EXPENSES (billing_expenses)
// ==========================================
export async function addExpense(expenseData) {
  if (!checkConfiguration()) return null;
  const { date, category, amount, recipient, description, status, paymentMethod, notes } = expenseData;
  if (!date || !category || !amount || !recipient) throw new Error("Missing required expense fields");

  try {
    const id = await getNextSeqId("billing_expenses", "BEXP-", "expenseId", 4);
    const docRef = doc(db, "billing_expenses", id);
    await setDoc(docRef, {
      expenseId: id,
      date: date || "",
      category: category || "Others",
      amount: Number(amount) || 0,
      recipient: recipient.trim(),
      description: description || "",
      status: status || "Paid",
      paymentMethod: paymentMethod || "Cash",
      notes: notes || "",
      createdAt: serverTimestamp()
    });
    return id;
  } catch (err) {
    console.error("Error adding expense:", err);
    throw err;
  }
}

export async function getAllExpenses() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "billing_expenses"));
    const expenses = [];
    querySnapshot.forEach(docSnap => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        data.id = docSnap.id;
        expenses.push(data);
      }
    });
    return expenses;
  } catch (err) {
    console.error("Error fetching expenses:", err);
    throw err;
  }
}

export async function updateExpense(expenseId, expenseData) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "billing_expenses", expenseId);
    await setDoc(docRef, { ...expenseData, updatedAt: serverTimestamp() }, { merge: true });
  } catch (err) {
    console.error("Error updating expense:", err);
    throw err;
  }
}

export async function deleteExpense(expenseId) {
  if (!checkConfiguration()) return;
  try {
    await deleteDoc(doc(db, "billing_expenses", expenseId));
  } catch (err) {
    console.error("Error deleting expense:", err);
    throw err;
  }
}

// ==========================================
// AUDIT LOGS (billing_tbl_audit_logs)
// ==========================================
export async function addAuditLog(logData) {
  if (!checkConfiguration()) return;
  const { user_email, action_type, collection_name, record_id, details } = logData;
  if (!user_email || !action_type || !details) throw new Error("Missing required audit log fields");
  try {
    const id = await getNextSeqId("billing_tbl_audit_logs", "BLOG-", "log_id", 5);
    const docRef = doc(db, "billing_tbl_audit_logs", id);
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
    const querySnapshot = await getDocs(collection(db, "billing_tbl_audit_logs"));
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
