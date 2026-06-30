from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from config.firebase import db

class EmployeeDatabaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_admin", password="password123", is_superuser=True)
        self.client = Client()
        self.client.force_login(self.user)
        self.created_employee_ids = []

    def tearDown(self):
        # Clean up any test employees created in Firestore
        for doc_id in self.created_employee_ids:
            try:
                db.collection('employees').document(doc_id).delete()
            except Exception:
                pass

    def test_employee_creation_with_multiple_roles(self):
        """
        Verify that we can create an employee with multiple roles/assignments,
        and that these roles are saved correctly in Firestore.
        """
        url = reverse('hrm:employee_database')
        
        post_data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@example.com',
            'phone': '1234567890',
            'basic_salary': '50000',
            'mobile_bill': '1000',
            'department': 'Engineering',
            'sub_department': 'Frontend Development',
            'position': 'Senior Frontend Developer',
            'employee_type': 'Permanent',
            'joining_date': '2026-01-01',
            'employment_status': 'Active',
            
            # Additional Roles
            'additional_dept': ['Client Services & Growth Department', 'Leadership & Strategic Management'],
            'additional_subdept': ['Training & Learning Development Team', ''],
            'additional_position': ['Lead Trainer', 'Co-Director']
        }
        
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)  # Should redirect
        
        # Verify employee was created in Firestore
        docs = db.collection('employees').where('email', '==', 'jane.doe@example.com').stream()
        employees = list(docs)
        self.assertEqual(len(employees), 1)
        
        emp_doc = employees[0]
        emp_data = emp_doc.to_dict()
        self.created_employee_ids.append(emp_doc.id)
        
        # Check basic details
        self.assertEqual(emp_data['name'], 'Jane Doe')
        self.assertEqual(emp_data['department'], 'Engineering')
        self.assertEqual(emp_data['sub_department'], 'Frontend Development')
        self.assertEqual(emp_data['position'], 'Senior Frontend Developer')
        
        # Check additional roles
        additional_roles = emp_data.get('additional_roles', [])
        self.assertEqual(len(additional_roles), 2)
        
        self.assertEqual(additional_roles[0]['department'], 'Client Services & Growth Department')
        self.assertEqual(additional_roles[0]['sub_department'], 'Training & Learning Development Team')
        self.assertEqual(additional_roles[0]['position'], 'Lead Trainer')
        
        self.assertEqual(additional_roles[1]['department'], 'Leadership & Strategic Management')
        self.assertEqual(additional_roles[1]['sub_department'], '')
        self.assertEqual(additional_roles[1]['position'], 'Co-Director')

    def test_employee_update_with_multiple_roles(self):
        """
        Verify that we can update an employee's multiple roles/assignments,
        and that these roles are updated correctly in Firestore.
        """
        # Create an employee directly in Firestore first
        test_emp_ref = db.collection('employees').add({
            'name': 'Bob Smith',
            'first_name': 'Bob',
            'last_name': 'Smith',
            'email': 'bob.smith@example.com',
            'phone': '9876543210',
            'basic_salary': 40000.0,
            'gross_salary': 89000.0,
            'department': 'Engineering',
            'sub_department': 'Backend Development',
            'position': 'Backend Engineer',
            'additional_roles': [
                {
                    'department': 'Support',
                    'sub_department': '',
                    'position': 'Support Specialist'
                }
            ],
            'status': 'Active'
        })
        doc_id = test_emp_ref[1].id
        self.created_employee_ids.append(doc_id)
        
        url = reverse('hrm:employee_database')
        
        # Send post request to update this employee
        post_data = {
            'doc_id': doc_id,
            'first_name': 'Bob',
            'last_name': 'Smith',
            'email': 'bob.smith@example.com',
            'phone': '9876543210',
            'basic_salary': '40000',
            'mobile_bill': '1000',
            'department': 'Engineering',
            'sub_department': 'Backend Development',
            'position': 'Backend Engineer',
            'employee_type': 'Permanent',
            'joining_date': '2026-01-01',
            'employment_status': 'Active',
            
            # Updated Additional Roles
            'additional_dept': ['Quality Assurance', 'Marketing'],
            'additional_subdept': ['', 'Growth Team'],
            'additional_position': ['QA Engineer', 'Marketing Advisor']
        }
        
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)  # Should redirect
        
        # Verify employee was updated in Firestore
        emp_doc = db.collection('employees').document(doc_id).get()
        emp_data = emp_doc.to_dict()
        
        # Check additional roles
        additional_roles = emp_data.get('additional_roles', [])
        self.assertEqual(len(additional_roles), 2)
        
        self.assertEqual(additional_roles[0]['department'], 'Quality Assurance')
        self.assertEqual(additional_roles[0]['position'], 'QA Engineer')
        self.assertEqual(additional_roles[1]['department'], 'Marketing')
        self.assertEqual(additional_roles[1]['position'], 'Marketing Advisor')
