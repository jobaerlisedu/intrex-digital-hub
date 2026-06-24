// assets/js/solution.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
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

// Initialize Firebase
let app, db, auth;
let isFirebaseConfigured = false;

if (firebaseConfig.apiKey && !firebaseConfig.apiKey.includes("placeholder-key")) {
  app = initializeApp(firebaseConfig);
  db = getFirestore(app);
  auth = getAuth(app);
  setPersistence(auth, browserSessionPersistence).catch((error) => {
    console.error("Failed to set auth persistence:", error);
  });
  isFirebaseConfigured = true;
} else {
  console.warn("Firebase configuration has not been set up.");
}

// Helper to check configuration state
function checkConfiguration() {
  if (!isFirebaseConfigured) {
    alert("Firebase configuration is not set up yet.");
    return false;
  }
  return true;
}

// Client-side key/ID auto-increment utility
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

// Project ID custom generator
async function generateProjectId() {
  const year = new Date().getFullYear();
  const prefix = `PRJ-${year}-`;
  return await getNextSeqId("sol_projects", prefix, "project_id", 3);
}

// ==========================================
// 1. ADMIN AUTHENTICATION
// ==========================================
export async function loginAdmin(email, password) {
  if (!checkConfiguration()) return null;
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  } catch (error) {
    console.error("Login failed: ", error);
    throw error;
  }
}

export async function logoutAdmin() {
  if (!checkConfiguration()) return;
  try {
    await signOut(auth);
  } catch (error) {
    console.error("Logout failed: ", error);
    throw error;
  }
}

export function onAdminAuthStateChanged(callback) {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    setTimeout(() => callback({ email: "admin@intrex-digital.com" }), 100);
    return;
  }
  if (!checkConfiguration()) return;
  onAuthStateChanged(auth, callback);
}

// ==========================================
// 2. PROJECT CREATOR (tbl_projects)
// ==========================================
export async function addProject(projectData) {
  if (!checkConfiguration()) return;
  const { project_id, project_name, client_sponsor, project_desc, start_date, end_date, project_status, project_manager } = projectData;
  if (!project_name || !client_sponsor || !start_date || !end_date || !project_manager) {
    throw new Error("Missing required project fields");
  }

  // Check project name uniqueness
  const querySnapshot = await getDocs(collection(db, "sol_projects"));
  let nameExists = false;
  querySnapshot.forEach(docSnap => {
    const data = docSnap.data();
    if (data.project_name && data.project_name.toLowerCase() === project_name.toLowerCase() && data.project_id !== project_id) {
      nameExists = true;
    }
  });
  if (nameExists) {
    throw new Error(`Project Name "${project_name}" is already in use.`);
  }

  try {
    const id = project_id ? project_id.trim().toUpperCase() : await generateProjectId();
    const docRef = doc(db, "sol_projects", id);
    await setDoc(docRef, {
      project_id: id,
      project_name: project_name.trim(),
      client_sponsor: client_sponsor.trim(),
      project_desc: project_desc ? project_desc.trim() : "",
      start_date: start_date,
      end_date: end_date,
      project_status: project_status || "Pipeline",
      project_manager: project_manager,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    });
    return id;
  } catch (error) {
    console.error("Error saving project: ", error);
    throw error;
  }
}

export async function getAllProjects() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    return [
      { project_id: "PRJ-2026-001", project_name: "Intrex Portal Revamp", client_sponsor: "CON-0001", project_status: "Active", start_date: "2026-01-01", end_date: "2026-12-31", project_manager: "EMP-0001" },
      { project_id: "PRJ-2026-002", project_name: "Government Cloud Infra", client_sponsor: "CON-0002", project_status: "Pipeline", start_date: "2026-06-01", end_date: "2026-11-30", project_manager: "EMP-0002" }
    ];
  }
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_projects"));
    const projects = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        projects.push(docSnap.data());
      }
    });
    return projects;
  } catch (error) {
    console.error("Error fetching projects: ", error);
    throw error;
  }
}

export async function deleteProject(projectId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_projects", projectId.trim().toUpperCase());
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting project: ", error);
    throw error;
  }
}

// ==========================================
// 3. CONTACT DIRECTORY (tbl_contacts)
// ==========================================
export async function addContact(contactData) {
  if (!checkConfiguration()) return;
  const { contact_id, project_id, contact_name, designation, organization, mobile_phone, email, contact_type } = contactData;
  if (!contact_name || !project_id || !designation || !organization) {
    throw new Error("Missing required contact fields");
  }

  // Check email uniqueness if provided
  if (email) {
    const querySnapshot = await getDocs(collection(db, "sol_contacts"));
    let emailExists = false;
    querySnapshot.forEach(docSnap => {
      const data = docSnap.data();
      if (data.email && data.email.toLowerCase() === email.toLowerCase() && data.contact_id !== contact_id) {
        emailExists = true;
      }
    });
    if (emailExists) {
      throw new Error(`Email ${email} is already in use by another contact.`);
    }
  }

  try {
    const id = contact_id || await getNextSeqId("sol_contacts", "CON-", "contact_id", 4);
    const docRef = doc(db, "sol_contacts", id);
    await setDoc(docRef, {
      contact_id: id,
      project_id: project_id, // Stored as array of strings
      contact_name: contact_name.trim(),
      designation: designation.trim(),
      organization: organization.trim(),
      mobile_phone: mobile_phone ? mobile_phone.trim() : "",
      email: email ? email.trim() : "",
      contact_type: contact_type || "Client",
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    });
    return id;
  } catch (error) {
    console.error("Error saving contact: ", error);
    throw error;
  }
}

export async function getAllContacts() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    return [
      { contact_id: "CON-0001", contact_name: "Jobaer Hossain", designation: "Sponsor", organization: "Intrex Digital", mobile_phone: "+8801711223344", email: "jobaer@intrex-digital.com", contact_type: "Client" },
      { contact_id: "CON-0002", contact_name: "Sarah Jenkins", designation: "Key Account Manager", organization: "Partner Inc.", mobile_phone: "+8801799887766", email: "sarah@partner.com", contact_type: "Client" },
      { contact_id: "CON-0003", contact_name: "Ali Ahmed", designation: "Vendor Lead", organization: "Apex Supplies", mobile_phone: "+8801555443322", email: "ali@apexsupplies.com", contact_type: "Vendor" },
      { contact_id: "CON-0004", contact_name: "Tariqul Islam", designation: "Distributor Manager", organization: "Summit Dist", mobile_phone: "+8801666778899", email: "tariqul@summitdist.com", contact_type: "Vendor" }
    ];
  }
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_contacts"));
    const contacts = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        contacts.push(docSnap.data());
      }
    });
    return contacts;
  } catch (error) {
    console.error("Error fetching contacts: ", error);
    throw error;
  }
}

export async function deleteContact(contactId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_contacts", contactId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting contact: ", error);
    throw error;
  }
}

// ==========================================
// 4. MEETING SCHEDULER (tbl_meetings)
// ==========================================
export async function addMeeting(meetingData) {
  if (!checkConfiguration()) return;
  const { meeting_id, project_id, meeting_title, meeting_timestamp, agenda, attendees_list, meeting_url, meeting_minutes } = meetingData;
  if (!project_id || !meeting_title || !meeting_timestamp || !attendees_list || attendees_list.length === 0) {
    throw new Error("Missing required meeting fields");
  }
  try {
    const id = meeting_id || await getNextSeqId("sol_meetings", "MTG-", "meeting_id", 4);
    const docRef = doc(db, "sol_meetings", id);
    await setDoc(docRef, {
      meeting_id: id,
      project_id: project_id.trim().toUpperCase(),
      meeting_title: meeting_title.trim(),
      meeting_timestamp: meeting_timestamp,
      agenda: agenda ? agenda.trim() : "",
      attendees_list: attendees_list, // Stored as array of emails
      meeting_url: meeting_url ? meeting_url.trim() : "",
      meeting_minutes: meeting_minutes ? meeting_minutes.trim() : "",
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    });
    return id;
  } catch (error) {
    console.error("Error saving meeting: ", error);
    throw error;
  }
}

export async function getAllMeetings() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_meetings"));
    const meetings = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        meetings.push(docSnap.data());
      }
    });
    return meetings;
  } catch (error) {
    console.error("Error fetching meetings: ", error);
    throw error;
  }
}

export async function deleteMeeting(meetingId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_meetings", meetingId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting meeting: ", error);
    throw error;
  }
}

// ==========================================
// 5. BUDGET PLANNER (tbl_budget)
// ==========================================
export async function addBudget(budgetData) {
  if (!checkConfiguration()) return;
  const { budget_line_id, project_id, cost_category, line_description, allocated_amount, approved_by } = budgetData;
  if (!project_id || !cost_category || !line_description || allocated_amount === undefined || !approved_by) {
    throw new Error("Missing required budget fields");
  }
  try {
    const id = budget_line_id || await getNextSeqId("sol_budget", "BGT-", "budget_line_id", 4);
    const docRef = doc(db, "sol_budget", id);
    await setDoc(docRef, {
      budget_line_id: id,
      project_id: project_id.trim().toUpperCase(),
      cost_category: cost_category.trim(),
      line_description: line_description.trim(),
      allocated_amount: Number(allocated_amount) || 0,
      approved_by: approved_by,
      last_updated: new Date().toISOString().substring(0, 10),
      createdAt: serverTimestamp()
    });
    return id;
  } catch (error) {
    console.error("Error saving budget configuration: ", error);
    throw error;
  }
}

export async function getAllBudgets() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_budget"));
    const budgets = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        budgets.push(docSnap.data());
      }
    });
    return budgets;
  } catch (error) {
    console.error("Error fetching budgets: ", error);
    throw error;
  }
}

export async function deleteBudget(budgetLineId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_budget", budgetLineId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting budget line: ", error);
    throw error;
  }
}

// ==========================================
// 6. TASKS & WORKING UPDATES (tbl_tasks)
// ==========================================
export async function addTask(taskData) {
  if (!checkConfiguration()) return;
  const { task_id, project_id, wbs_code, task_name, assigned_to, task_startDate, task_endDate, progress_percent, task_status, working_update } = taskData;
  if (!project_id || !task_name || !assigned_to || !task_startDate || !task_endDate || progress_percent === undefined) {
    throw new Error("Missing required task fields");
  }
  try {
    const id = task_id || await getNextSeqId("sol_tasks", "TSK-", "task_id", 4);
    const docRef = doc(db, "sol_tasks", id);

    // Read previous task document if existing to support append-only log visualizer
    let finalUpdate = working_update ? working_update.trim() : "";
    if (task_id) {
      const existingSnap = await getDoc(docRef);
      if (existingSnap.exists()) {
        const existingData = existingSnap.data();
        if (existingData.working_update && working_update && existingData.working_update !== working_update) {
          // If the text is new and doesn't already contain the existing logs, append/prepend
          if (!working_update.includes(existingData.working_update)) {
            finalUpdate = existingData.working_update + "\n" + working_update.trim();
          }
        } else if (existingData.working_update && !working_update) {
          finalUpdate = existingData.working_update;
        }
      }
    }

    await setDoc(docRef, {
      task_id: id,
      project_id: project_id.trim().toUpperCase(),
      wbs_code: wbs_code ? wbs_code.trim() : "1.0",
      task_name: task_name.trim(),
      assigned_to: assigned_to,
      task_startDate: task_startDate,
      task_endDate: task_endDate,
      progress_percent: Number(progress_percent) || 0,
      task_status: task_status || "Not Started",
      working_update: finalUpdate,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    });

    // Cascade update the project status if the task is set to Completed/In Progress
    if (task_status === "Completed" || task_status === "In Progress") {
      const projRef = doc(db, "sol_projects", project_id.trim().toUpperCase());
      const projSnap = await getDoc(projRef);
      if (projSnap.exists()) {
        const currentProjStatus = projSnap.data().project_status;
        if (task_status === "In Progress" && currentProjStatus === "Pipeline") {
          await setDoc(projRef, { project_status: "Active", updatedAt: serverTimestamp() }, { merge: true });
        }
      }
    }

    return id;
  } catch (error) {
    console.error("Error saving task: ", error);
    throw error;
  }
}

export async function getAllTasks() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_tasks"));
    const tasks = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        tasks.push(docSnap.data());
      }
    });
    return tasks;
  } catch (error) {
    console.error("Error fetching tasks: ", error);
    throw error;
  }
}

export async function deleteTask(taskId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_tasks", taskId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting task: ", error);
    throw error;
  }
}

// ==========================================
// 7. PURCHASE REQUISITIONS (tbl_requisitions)
// ==========================================
// Requisition ID custom generator REQ-YYYY-XXXX
async function generateRequisitionId() {
  const year = new Date().getFullYear();
  const prefix = `REQ-${year}-`;
  return await getNextSeqId("sol_requisitions", prefix, "requisition_id", 4);
}

// ==========================================
// 7. PURCHASE REQUISITIONS (tbl_requisitions)
// ==========================================
export async function addRequisition(reqData) {
  if (!checkConfiguration()) return;
  const { requisition_id, project_id, item_category, item_description, qty_requested, est_unit_cost, dept_approval, rejection_reason } = reqData;
  if (!project_id || !item_category || !item_description || qty_requested === undefined || est_unit_cost === undefined || !dept_approval) {
    throw new Error("Missing required requisition fields");
  }

  // Validate item description length >= 10
  if (item_description.trim().length < 10) {
    throw new Error("Item Description must be at least 10 characters long.");
  }

  // Validate quantity >= 1
  if (Number(qty_requested) < 1 || !Number.isInteger(Number(qty_requested))) {
    throw new Error("Quantity Requested must be a positive whole number >= 1.");
  }

  // Validate unit cost > 0
  if (Number(est_unit_cost) <= 0) {
    throw new Error("Estimated Unit Cost must be greater than 0.00.");
  }

  // Validate rejection reason if rejected
  if (dept_approval === "Rejected" && (!rejection_reason || !rejection_reason.trim())) {
    throw new Error("Rejection Reason is required when approval status is Rejected.");
  }

  try {
    const id = requisition_id || await generateRequisitionId();
    const docRef = doc(db, "sol_requisitions", id);
    const total = Number(qty_requested) * Number(est_unit_cost);

    await setDoc(docRef, {
      requisition_id: id,
      project_id: project_id.trim().toUpperCase(),
      item_category: item_category,
      item_description: item_description.trim(),
      qty_requested: Number(qty_requested),
      est_unit_cost: Number(est_unit_cost),
      est_total_cost: Number(total.toFixed(2)), // Calculated field
      dept_approval: dept_approval || "Pending Review",
      rejection_reason: dept_approval === "Rejected" ? rejection_reason.trim() : "",
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    });
    return id;
  } catch (error) {
    console.error("Error saving requisition: ", error);
    throw error;
  }
}

export async function getAllRequisitions() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_requisitions"));
    const reqs = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        reqs.push(docSnap.data());
      }
    });
    return reqs;
  } catch (error) {
    console.error("Error fetching requisitions: ", error);
    throw error;
  }
}

export async function deleteRequisition(requisitionId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_requisitions", requisitionId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting requisition: ", error);
    throw error;
  }
}

// ==========================================
// 8. PURCHASE ORDER MANAGEMENT (tbl_purchase_orders)
// ==========================================
export async function addPurchaseOrder(poData) {
  if (!checkConfiguration()) return;
  const { po_number, requisition_id, project_id, vendor_name, final_po_total, payment_terms, po_issue_date, po_status } = poData;
  if (!requisition_id || !project_id || !vendor_name || final_po_total === undefined || !payment_terms || !po_issue_date || !po_status) {
    throw new Error("Missing required purchase order fields");
  }

  // Validate PO Issue Date is not in future
  const issueDate = new Date(po_issue_date);
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  if (issueDate > today) {
    throw new Error("PO Issue Date cannot be in the future.");
  }

  // Check unique requisition_id
  const querySnapshot = await getDocs(collection(db, "sol_purchase_orders"));
  let reqExists = false;
  querySnapshot.forEach(docSnap => {
    const data = docSnap.data();
    if (data.requisition_id === requisition_id && data.po_number !== po_number) {
      reqExists = true;
    }
  });
  if (reqExists) {
    throw new Error(`A Purchase Order is already associated with Requisition ID ${requisition_id}.`);
  }

  try {
    const id = po_number || await getNextSeqId("sol_purchase_orders", "PO-", "po_number", 5);
    const docRef = doc(db, "sol_purchase_orders", id);
    await setDoc(docRef, {
      po_number: id,
      requisition_id: requisition_id,
      project_id: project_id.trim().toUpperCase(),
      vendor_name: vendor_name.trim(),
      final_po_total: Number(final_po_total) || 0,
      payment_terms: payment_terms,
      po_issue_date: po_issue_date,
      po_status: po_status || "PO Issued",
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    });

    // Cascade update: update requisition status
    const reqRef = doc(db, "sol_requisitions", requisition_id);
    const reqSnap = await getDoc(reqRef);
    if (reqSnap.exists()) {
      await setDoc(reqRef, { dept_approval: "Approved", updatedAt: serverTimestamp() }, { merge: true });
    }

    // Cascade add to Expense tracker automatically (ledger of truth)
    const expenseId = "EXP-AUTO-" + id;
    const expRef = doc(db, "sol_expenses", expenseId);
    await setDoc(expRef, {
      expense_id: expenseId,
      project_id: project_id.trim().toUpperCase(),
      expense_routing_type: "PO-Backed",
      po_number_ref: id,
      vendor_invoice_num: "INV-PO-" + id,
      invoice_amount: Number(final_po_total) || 0,
      amount_paid: 0,
      payment_status: "Unpaid / Awaiting Approval",
      payment_method: "ACH / Wire Transfer",
      clearance_date: "",
      createdAt: serverTimestamp()
    });

    return id;
  } catch (error) {
    console.error("Error saving purchase order: ", error);
    throw error;
  }
}

export async function getAllPurchaseOrders() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_purchase_orders"));
    const purchases = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        purchases.push(docSnap.data());
      }
    });
    return purchases;
  } catch (error) {
    console.error("Error fetching purchase orders: ", error);
    throw error;
  }
}

export async function deletePurchaseOrder(poNumber) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_purchase_orders", poNumber);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting purchase order: ", error);
    throw error;
  }
}

// ==========================================
// 9. COST / EXPENSE LEDGER (tbl_expenses)
// ==========================================
export async function addExpense(expenseData) {
  if (!checkConfiguration()) return;
  let { expense_id, project_id, expense_routing_type, po_number_ref, vendor_invoice_num, invoice_amount, amount_paid, payment_status, payment_method, clearance_date } = expenseData;
  if (!project_id || !expense_routing_type || !vendor_invoice_num || invoice_amount === undefined || amount_paid === undefined || !payment_status || !payment_method) {
    throw new Error("Missing required expense fields");
  }

  // Validate PO reference for PO-Backed routing
  if (expense_routing_type === "PO-Backed" && (!po_number_ref || !po_number_ref.trim())) {
    throw new Error("PO Number Reference is required for PO-Backed expenses.");
  }

  // Validate paid amount does not exceed invoice amount
  if (Number(amount_paid) > Number(invoice_amount)) {
    throw new Error("Amount Paid To Date cannot exceed Invoice Gross Amount.");
  }

  // Validate clearance date based on payment status
  if (payment_status === "Unpaid / Awaiting Approval") {
    clearance_date = "";
  } else if ((payment_status === "Partially Paid" || payment_status === "Fully Settled") && !clearance_date) {
    throw new Error("Clearance Date is required when status is Partial or Fully Settled.");
  }

  try {
    const id = expense_id || await getNextSeqId("sol_expenses", "EXP-", "expense_id", 5);
    const docRef = doc(db, "sol_expenses", id);
    await setDoc(docRef, {
      expense_id: id,
      project_id: project_id.trim().toUpperCase(),
      expense_routing_type: expense_routing_type,
      po_number_ref: expense_routing_type === "PO-Backed" ? po_number_ref : "",
      vendor_invoice_num: vendor_invoice_num.trim(),
      invoice_amount: Number(invoice_amount) || 0,
      amount_paid: Number(amount_paid) || 0,
      payment_status: payment_status,
      payment_method: payment_method,
      clearance_date: clearance_date || "",
      createdAt: serverTimestamp()
    });
    return id;
  } catch (error) {
    console.error("Error saving expense entry: ", error);
    throw error;
  }
}

export async function getAllExpenses() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_expenses"));
    const expenses = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        expenses.push(docSnap.data());
      }
    });
    return expenses;
  } catch (error) {
    console.error("Error fetching expenses: ", error);
    throw error;
  }
}

export async function deleteExpense(expenseId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_expenses", expenseId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting expense entry: ", error);
    throw error;
  }
}

// ==========================================
// 10. EMPLOYEE INFORMATION DATABASE (tbl_employees)
// ==========================================
export async function addEmployee(employeeData) {
  throw new Error("Employees must be managed centrally from the HR Dashboard.");
}

export async function getAllEmployees() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "hr_employees"));
    const employees = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        employees.push({
          employee_id: data.emp_id || "",
          employee_name: data.name || `${data.firstName || ''} ${data.lastName || ''}`.trim(),
          designation: data.position || "",
          department: data.department || "",
          subDepartment: data.subDepartment || "",
          mobile_phone: data.phone || "",
          email: data.email || "",
          status: data.employmentStatus || data.status || "Active",
          createdAt: data.createdAt,
          updatedAt: data.updatedAt
        });
      }
    });
    return employees;
  } catch (error) {
    console.error("Error fetching employees: ", error);
    throw error;
  }
}

export async function deleteEmployee(employeeId) {
  throw new Error("Employees must be managed centrally from the HR Dashboard.");
}

export async function getAllDepartments() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "hr_departments"));
    const depts = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        depts.push(docSnap.data());
      }
    });
    return depts;
  } catch (error) {
    console.error("Error fetching departments: ", error);
    throw error;
  }
}

// ==========================================
// 11. SUPPORT TICKETING & SLA (tbl_support_tickets)
// ==========================================
export async function addSupportTicket(ticketData) {
  if (!checkConfiguration()) return;
  const {
    ticket_id, project_id, requester_id, ticket_subject,
    ticket_desc, priority, assigned_to, ticket_status, resolution_notes,
    asset_id
  } = ticketData;

  if (!project_id || !requester_id || !ticket_subject || !ticket_desc || !priority || !ticket_status) {
    throw new Error("Missing required ticket fields");
  }

  if (ticket_subject.trim().length > 150) {
    throw new Error("Subject/Summary cannot exceed 150 characters.");
  }

  // Validate resolution notes before resolving/closing
  const isClosedStatus = ticket_status === "Resolved" || ticket_status === "Closed";
  if (isClosedStatus && (!resolution_notes || !resolution_notes.trim())) {
    throw new Error("Resolution Notes are required before resolving or closing a ticket.");
  }

  try {
    const id = ticket_id || await getNextSeqId("sol_support_tickets", "TCK-", "ticket_id", 4);
    const docRef = doc(db, "sol_support_tickets", id);

    let createdAt = new Date().toISOString();
    let closedAt = "";

    if (ticket_id) {
      // Fetch existing ticket to preserve created_at and handle status transitions
      const snap = await getDoc(docRef);
      if (snap.exists()) {
        const data = snap.data();
        createdAt = data.created_at || createdAt;

        const origWasClosed = data.ticket_status === "Resolved" || data.ticket_status === "Closed";
        if (isClosedStatus) {
          closedAt = origWasClosed ? (data.closed_at || new Date().toISOString()) : new Date().toISOString();
        } else {
          closedAt = "";
        }
      }
    } else {
      // New ticket
      if (isClosedStatus) {
        closedAt = new Date().toISOString();
      }
    }

    // SLA Deadline calculation
    const baseDate = new Date(createdAt);
    let hoursToAdd = 72; // Default Medium
    if (priority === "Low") hoursToAdd = 168;
    else if (priority === "High") hoursToAdd = 24;
    else if (priority === "Critical") hoursToAdd = 4;

    baseDate.setHours(baseDate.getHours() + hoursToAdd);
    const slaDeadline = baseDate.toISOString();

    await setDoc(docRef, {
      ticket_id: id,
      project_id: project_id.trim().toUpperCase(),
      requester_id: requester_id,
      ticket_subject: ticket_subject.trim(),
      ticket_desc: ticket_desc.trim(),
      priority: priority,
      assigned_to: assigned_to || "",
      ticket_status: ticket_status,
      resolution_notes: isClosedStatus ? resolution_notes.trim() : "",
      created_at: createdAt,
      closed_at: closedAt,
      sla_deadline: slaDeadline,
      asset_id: asset_id || "",
      updated_at: serverTimestamp()
    });

    return id;
  } catch (error) {
    console.error("Error saving support ticket: ", error);
    throw error;
  }
}

export async function getAllSupportTickets() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_support_tickets"));
    const tickets = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        tickets.push(docSnap.data());
      }
    });
    return tickets;
  } catch (error) {
    console.error("Error fetching support tickets: ", error);
    throw error;
  }
}

export async function deleteSupportTicket(ticketId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_support_tickets", ticketId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting support ticket: ", error);
    throw error;
  }
}

// ==========================================
// 12. CLIENT INVOICING & REVENUE (tbl_client_payments)
// ==========================================
async function generateInvoiceId() {
  const year = new Date().getFullYear();
  const prefix = `INV-${year}-`;
  return await getNextSeqId("sol_client_payments", prefix, "invoice_id", 3);
}

export async function addClientPayment(paymentData) {
  if (!checkConfiguration()) return;
  const {
    invoice_id, project_id, milestone_type, invoice_date,
    due_date, invoiced_amount, amount_received, payment_status,
    date_received, transaction_ref
  } = paymentData;

  if (!project_id || !milestone_type || !invoice_date || !due_date || invoiced_amount === undefined || !payment_status) {
    throw new Error("Missing required client payment fields");
  }

  if (Number(invoiced_amount) <= 0) {
    throw new Error("Invoiced Amount must be greater than 0.00.");
  }

  const invDate = new Date(invoice_date);
  const dueDate = new Date(due_date);
  if (dueDate <= invDate) {
    throw new Error("Payment Due Date must be greater than Invoice Issue Date.");
  }

  const amtReceived = Number(amount_received) || 0;
  if (amtReceived > 0 && (!date_received || !date_received.trim())) {
    throw new Error("Date Received is required when Amount Received is greater than 0.00.");
  }

  try {
    const id = invoice_id || await generateInvoiceId();
    const docRef = doc(db, "sol_client_payments", id);
    const outstanding = Number(invoiced_amount) - amtReceived;

    await setDoc(docRef, {
      invoice_id: id,
      project_id: project_id.trim().toUpperCase(),
      milestone_type: milestone_type,
      invoice_date: invoice_date,
      due_date: due_date,
      invoiced_amount: Number(invoiced_amount),
      amount_received: amtReceived,
      outstanding_balance: Number(outstanding.toFixed(2)),
      payment_status: payment_status,
      date_received: amtReceived > 0 ? date_received : "",
      transaction_ref: transaction_ref ? transaction_ref.trim() : "",
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    }, { merge: true });

    return id;
  } catch (error) {
    console.error("Error saving client payment invoice: ", error);
    throw error;
  }
}

export async function getAllClientPayments() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_client_payments"));
    const payments = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        payments.push(docSnap.data());
      }
    });
    return payments;
  } catch (error) {
    console.error("Error fetching client payments: ", error);
    throw error;
  }
}

export async function deleteClientPayment(invoiceId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_client_payments", invoiceId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting client payment record: ", error);
    throw error;
  }
}

// ==========================================
// 13. DOMAIN & HOSTING SALES TRACKER (tbl_domain_hosting_sales)
// ==========================================
async function generateAssetId() {
  return await getNextSeqId("sol_domain_hosting_sales", "AST-", "asset_id", 4);
}

export async function addDomainHosting(assetData) {
  if (!checkConfiguration()) return;
  const {
    asset_id, project_id, asset_type, asset_url, provider_name,
    cost_price, selling_price, reg_date, billing_cycle, renewal_date, asset_status,
    package_name, hosting_capacity
  } = assetData;

  if (!project_id || !asset_type || !asset_url || !provider_name || cost_price === undefined || selling_price === undefined || !reg_date || !billing_cycle || !renewal_date || !asset_status) {
    throw new Error("Missing required domain & hosting fields");
  }

  if (Number(cost_price) < 0) {
    throw new Error("Cost Price cannot be negative.");
  }

  if (Number(selling_price) <= Number(cost_price)) {
    throw new Error("Selling Price must be strictly greater than Cost Price.");
  }

  if (!asset_url.trim()) {
    throw new Error("Domain/Server URL is required.");
  }

  try {
    const id = asset_id || await generateAssetId();
    const docRef = doc(db, "sol_domain_hosting_sales", id);

    await setDoc(docRef, {
      asset_id: id,
      project_id: project_id.trim().toUpperCase(),
      package_name: package_name ? package_name.trim() : "",
      hosting_capacity: hosting_capacity ? hosting_capacity.trim() : "",
      asset_type: asset_type,
      asset_url: asset_url.trim(),
      provider_name: provider_name,
      cost_price: Number(cost_price),
      selling_price: Number(selling_price),
      reg_date: reg_date,
      billing_cycle: billing_cycle,
      renewal_date: renewal_date,
      asset_status: asset_status,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    }, { merge: true });

    return id;
  } catch (error) {
    console.error("Error saving domain & hosting asset: ", error);
    throw error;
  }
}

export async function getAllDomainHosting() {
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_domain_hosting_sales"));
    const assets = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        assets.push(docSnap.data());
      }
    });
    return assets;
  } catch (error) {
    console.error("Error fetching domain & hosting assets: ", error);
    throw error;
  }
}

export async function deleteDomainHosting(assetId) {
  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "sol_domain_hosting_sales", assetId);
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting domain & hosting asset: ", error);
    throw error;
  }
}

// ==========================================
// 14. AUDIT LOGS SYSTEM (tbl_audit_logs)
// ==========================================
export async function addAuditLog(logData) {
  if (!checkConfiguration()) return;
  const { user_email, action_type, collection_name, record_id, details } = logData;
  if (!user_email || !action_type || !details) {
    throw new Error("Missing required audit log fields");
  }
  try {
    const id = await getNextSeqId("sol_audit_logs", "LOG-", "log_id", 5);
    const docRef = doc(db, "sol_audit_logs", id);
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
  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "sol_audit_logs"));
    const logs = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        logs.push(docSnap.data());
      }
    });
    // Sort logs descending (newest first) by log_id
    logs.sort((a, b) => b.log_id.localeCompare(a.log_id));
    return logs;
  } catch (error) {
    console.error("Error fetching audit logs: ", error);
    throw error;
  }
}

export async function getAllOnlineInquiries() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    return [
      {
        inquiryKey: "INQ-981023",
        status: "New",
        name: "Rahat Khan",
        email: "rahat@example.com",
        phone: "+8801911223344",
        subject: "Network Architecture Consultation",
        source: "home-page",
        createdAt: new Date(),
        message: "We are looking to design a hybrid enterprise network for our new head office in Dhaka."
      },
      {
        inquiryKey: "INQ-981024",
        status: "Replied",
        name: "Sadia Rahman",
        email: "sadia@example.com",
        phone: "+8801811223344",
        subject: "Cloud Migration Service",
        source: "service-cloud",
        createdAt: new Date(Date.now() - 86400000),
        message: "Can you provide a price quotation for migrating our on-premise VMs to AWS?"
      }
    ];
  }

  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "learn_online_inquiries"));
    const inquiries = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) inquiries.push(docSnap.data());
    });
    inquiries.sort((a, b) => {
      const timeA = a.createdAt?.toDate ? a.createdAt.toDate().getTime() : new Date(a.createdAt || 0).getTime();
      const timeB = b.createdAt?.toDate ? b.createdAt.toDate().getTime() : new Date(b.createdAt || 0).getTime();
      return timeB - timeA;
    });
    return inquiries;
  } catch (error) {
    console.error("Error fetching online inquiries: ", error);
    throw error;
  }
}

export async function deleteOnlineInquiry(inquiryKey) {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    console.log("Mock delete inquiry: ", inquiryKey);
    return;
  }

  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "learn_online_inquiries", inquiryKey.trim().toUpperCase());
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting online inquiry: ", error);
    throw error;
  }
}

export async function getAllNewsletterSubscriptions() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    return [
      {
        email: "subscriber1@example.com",
        createdAt: new Date()
      },
      {
        email: "subscriber2@example.com",
        createdAt: new Date(Date.now() - 86400000)
      }
    ];
  }

  if (!checkConfiguration()) return [];
  try {
    const querySnapshot = await getDocs(collection(db, "learn_newsletter_subscriptions"));
    const subs = [];
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) subs.push(docSnap.data());
    });
    subs.sort((a, b) => {
      const timeA = a.createdAt?.toDate ? a.createdAt.toDate().getTime() : new Date(a.createdAt || 0).getTime();
      const timeB = b.createdAt?.toDate ? b.createdAt.toDate().getTime() : new Date(b.createdAt || 0).getTime();
      return timeB - timeA;
    });
    return subs;
  } catch (error) {
    console.error("Error fetching newsletter subscriptions: ", error);
    throw error;
  }
}

export async function deleteNewsletterSubscription(email) {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mock') === '1') {
    console.log("Mock delete newsletter subscription: ", email);
    return;
  }

  if (!checkConfiguration()) return;
  try {
    const docRef = doc(db, "learn_newsletter_subscriptions", email.trim().toLowerCase());
    await deleteDoc(docRef);
  } catch (error) {
    console.error("Error deleting newsletter subscription: ", error);
    throw error;
  }
}



