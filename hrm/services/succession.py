import json
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
from ..models import KeyPosition, SuccessorCandidate, SuccessionPlan


class SuccessionService:
    @staticmethod
    def add_key_position(data):
        doc_id = data.get('doc_id')
        if doc_id:
            kp = KeyPosition.objects.get(id=doc_id)
            kp.position_title = data.get('position_title')
            kp.risk_of_vacancy = data.get('risk_of_vacancy')
            kp.readiness_gap = data.get('readiness_gap')
            kp.status = data.get('status', 'Active')
            kp.save()
            return 'updated'
        else:
            KeyPosition.objects.create(
                position_title=data.get('position_title'),
                risk_of_vacancy=data.get('risk_of_vacancy'),
                readiness_gap=data.get('readiness_gap'),
                status=data.get('status', 'Active'),
            )
            return 'created'

    @staticmethod
    def add_successor(data):
        succ_id = data.get('id')
        if succ_id:
            sc = SuccessorCandidate.objects.get(id=succ_id)
            sc.readiness = data.get('readiness')
            sc.strengths = data.get('strengths', '')
            sc.development_needs = data.get('development_needs', '')
            sc.is_primary = data.get('is_primary') == 'on'
            sc.save()
            return 'updated'
        else:
            kp_id = data.get('key_position_id')
            emp_id = data.get('employee_id')
            if kp_id and emp_id:
                SuccessorCandidate.objects.create(
                    key_position_id=kp_id, employee_id=emp_id,
                    readiness=data.get('readiness'),
                    strengths=data.get('strengths', ''),
                    development_needs=data.get('development_needs', ''),
                    is_primary=data.get('is_primary') == 'on',
                )
                return 'created'
        return None

    @staticmethod
    def add_plan(data):
        doc_id = data.get('doc_id')
        if doc_id:
            sp = SuccessionPlan.objects.get(id=doc_id)
            sp.title = data.get('title')
            sp.description = data.get('description', '')
            sp.review_date = data.get('review_date')
            sp.status = data.get('status', 'Draft')
            sp.save()
            return 'updated'
        else:
            SuccessionPlan.objects.create(
                title=data.get('title'),
                description=data.get('description', ''),
                review_date=data.get('review_date'),
                status=data.get('status', 'Draft'),
            )
            return 'created'
