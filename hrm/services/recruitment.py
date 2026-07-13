import random
import uuid
from config.logger import hrm_logger
from .base import ORMService
from ..models import (
    RecruitmentCandidate, RecruitmentShortlist,
    RecruitmentInterview, RecruitmentSelection, Position, Department,
)


class RecruitmentService(ORMService):
    model = RecruitmentCandidate

    @classmethod
    def _resolve(cls, doc_id):
        if not doc_id:
            return None
        try:
            return cls.model.objects.get(pk=doc_id)
        except (cls.model.DoesNotExist, ValueError):
            pass
        return cls.model.objects.filter(pk=doc_id).first()

    @classmethod
    def _resolve_candidate(cls, cand_doc_id):
        if not cand_doc_id:
            return None
        try:
            return RecruitmentCandidate.objects.get(pk=cand_doc_id)
        except (RecruitmentCandidate.DoesNotExist, ValueError):
            pass
        return RecruitmentCandidate.objects.filter(pk=cand_doc_id).first()

    @classmethod
    def add_candidate(cls, data, user):
        doc_id = data.get('doc_id')
        from datetime import date
        today_str = str(date.today())
        date_applied = data.get('date_applied') or today_str

        if doc_id:
            instance = cls._resolve(doc_id)
            if instance:
                instance.name = data.get('name', instance.name)
                instance.position = data.get('position', instance.position)
                instance.status = data.get('status', instance.status)
                instance.notes = data.get('notes', '')
                instance.date_applied = date_applied
                instance.save()
            return 'updated'
        else:
            cand_id = f"CAN-{random.randint(100, 999)}"
            instance = RecruitmentCandidate.objects.create(
                cand_id=cand_id,
                name=data.get('name', ''),
                position=data.get('position', ''),
                status=data.get('status', 'New'),
                notes=data.get('notes', ''),
                date_applied=date_applied,
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def add_shortlist(cls, data, user):
        cand_id = data.get('candidate_id')
        candidate = cls._resolve_candidate(cand_id)
        if not candidate:
            return None

        candidate.status = 'Shortlisted'
        candidate.save(update_fields=['status'])

        doc_id = data.get('doc_id')
        if doc_id:
            instance = RecruitmentShortlist.objects.filter(pk=doc_id).first()
            if instance:
                instance.rating = data.get('rating', instance.rating)
                instance.experience = data.get('experience', instance.experience)
                instance.save()
            return 'updated'
        else:
            instance = RecruitmentShortlist.objects.create(
                candidate=candidate,
                name=candidate.name,
                position=candidate.position,
                rating=data.get('rating'),
                experience=data.get('experience'),
            )
            return 'created'

    @classmethod
    def schedule_interview(cls, data, user):
        cand_id = data.get('candidate_id')
        candidate = cls._resolve_candidate(cand_id)
        if not candidate:
            return None

        candidate.status = 'Interview'
        candidate.save(update_fields=['status'])

        doc_id = data.get('doc_id')
        if doc_id:
            instance = RecruitmentInterview.objects.filter(pk=doc_id).first()
            if instance:
                instance.interviewer = data.get('interviewer', instance.interviewer)
                instance.date_time = data.get('date_time', instance.date_time)
                instance.status = data.get('status', instance.status)
                instance.save()
            return 'updated'
        else:
            instance = RecruitmentInterview.objects.create(
                candidate=candidate,
                name=candidate.name,
                position=candidate.position,
                interviewer=data.get('interviewer', ''),
                date_time=data.get('date_time'),
                status=data.get('status', 'Scheduled'),
            )
            return 'created'

    @classmethod
    def add_selection(cls, data, user):
        cand_id = data.get('candidate_id')
        candidate = cls._resolve_candidate(cand_id)
        if not candidate:
            return None

        offer_status = data.get('offer_status')
        new_status = 'Selected' if offer_status in ['Offered', 'Accepted', 'Joined'] else 'Rejected'
        candidate.status = new_status
        candidate.save(update_fields=['status'])

        doc_id = data.get('doc_id')
        if doc_id:
            instance = RecruitmentSelection.objects.filter(pk=doc_id).first()
            if instance:
                instance.offer_status = offer_status or instance.offer_status
                instance.offer_date = data.get('offer_date', instance.offer_date)
                instance.save()
            return 'updated'
        else:
            instance = RecruitmentSelection.objects.create(
                candidate=candidate,
                name=candidate.name,
                position=candidate.position,
                offer_status=offer_status or 'Offered',
                offer_date=data.get('offer_date'),
            )
            return 'created'

    @classmethod
    def delete(cls, doc_id):
        for model_class in [RecruitmentCandidate, RecruitmentShortlist,
                            RecruitmentInterview, RecruitmentSelection]:
            model_class.objects.filter(pk=doc_id).update(is_active=False)
        for model_class in [RecruitmentCandidate, RecruitmentShortlist,
                            RecruitmentInterview, RecruitmentSelection]:
            try:
                obj = model_class.objects.get(pk=doc_id)
                obj.is_active = False
                obj.save(update_fields=['is_active'])
            except (model_class.DoesNotExist, ValueError):
                pass

    @classmethod
    def delete_interview(cls, doc_id):
        RecruitmentInterview.objects.filter(pk=doc_id).update(is_active=False)
        try:
            obj = RecruitmentInterview.objects.get(pk=doc_id)
            obj.is_active = False
            obj.save(update_fields=['is_active'])
        except (RecruitmentInterview.DoesNotExist, ValueError):
            pass

    @classmethod
    def delete_selection(cls, doc_id):
        RecruitmentSelection.objects.filter(pk=doc_id).update(is_active=False)
        try:
            obj = RecruitmentSelection.objects.get(pk=doc_id)
            obj.is_active = False
            obj.save(update_fields=['is_active'])
        except (RecruitmentSelection.DoesNotExist, ValueError):
            pass

    @classmethod
    def update_stage(cls, doc_id, new_stage, user):
        candidate = cls._resolve(doc_id)
        if candidate:
            candidate.status = new_stage
            candidate.save(update_fields=['status'])

    @classmethod
    def get_candidates(cls):
        candidates = list(RecruitmentCandidate.objects.filter(is_active=True).values(
            'pk', 'cand_id', 'name', 'position', 'status', 'notes', 'date_applied', 'source', 'rating', 'created_at',
        ))
        for c in candidates:
            c['id'] = c.pop('pk') or ''
            c['date_applied'] = str(c['date_applied']) if c['date_applied'] else ''

        shortlists = list(RecruitmentShortlist.objects.filter(is_active=True).select_related('candidate').values(
            'pk', 'candidate__name', 'candidate__position', 'rating', 'experience', 'created_at',
        ))
        for s in shortlists:
            s['id'] = s.pop('pk') or ''
            s['name'] = s.pop('candidate__name', '')
            s['position'] = s.pop('candidate__position', '')

        interviews = list(RecruitmentInterview.objects.filter(is_active=True).select_related('candidate').values(
            'pk', 'candidate__name', 'candidate__position', 'interviewer', 'date_time', 'status',
        ))
        for i in interviews:
            i['id'] = i.pop('pk') or ''
            i['name'] = i.pop('candidate__name', '')
            i['position'] = i.pop('candidate__position', '')

        selections = list(RecruitmentSelection.objects.filter(is_active=True).select_related('candidate').values(
            'pk', 'candidate__name', 'candidate__position', 'offer_status', 'offer_date',
        ))
        for s in selections:
            s['id'] = s.pop('pk') or ''
            s['name'] = s.pop('candidate__name', '')
            s['position'] = s.pop('candidate__position', '')

        return candidates, shortlists, interviews, selections
