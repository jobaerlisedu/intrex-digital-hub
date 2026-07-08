(function() {
    'use strict';

    window.switchTab = function(tab) {
        const formDiv = document.getElementById('tab-form');
        const listDiv = document.getElementById('tab-list');
        const formBtn = document.getElementById('tab-form-btn');
        const listBtn = document.getElementById('tab-list-btn');
        if (!formDiv || !listDiv) return;
        if (tab === 'form') {
            formDiv.style.display = 'block';
            listDiv.style.display = 'none';
            if (formBtn) { formBtn.style.background = 'var(--accent-color)'; formBtn.style.color = '#fff'; }
            if (listBtn) { listBtn.style.background = 'transparent'; listBtn.style.color = '#64748b'; }
        } else {
            formDiv.style.display = 'none';
            listDiv.style.display = 'block';
            if (listBtn) { listBtn.style.background = 'var(--accent-color)'; listBtn.style.color = '#fff'; }
            if (formBtn) { formBtn.style.background = 'transparent'; formBtn.style.color = '#64748b'; }
        }
    };

    window.crudEditRecord = function(id, db, fieldMap, opts) {
        opts = opts || {};
        var data = db.find(function(item) { return item.id === id; });
        if (!data) return;
        window.switchTab('form');
        document.getElementById('doc_id').value = id;
        for (var field in fieldMap) {
            var el = document.getElementById(field);
            if (el) el.value = data[fieldMap[field]] !== undefined ? data[fieldMap[field]] : '';
        }
        var ft = document.getElementById('form-title');
        if (ft && opts.formTitle) ft.innerHTML = opts.formTitle;
        var bs = document.getElementById('btn-save');
        if (bs && opts.saveBtnHtml) bs.innerHTML = opts.saveBtnHtml;
        var bc = document.getElementById('btn-cancel');
        if (bc) bc.style.display = 'flex';
    };

    window.crudCancelEdit = function(formId, opts) {
        opts = opts || {};
        document.getElementById('doc_id').value = '';
        var f = document.getElementById(formId);
        if (f) f.reset();
        var ft = document.getElementById('form-title');
        if (ft && opts.formTitle) ft.innerHTML = opts.formTitle;
        var bs = document.getElementById('btn-save');
        if (bs && opts.saveBtnHtml) bs.innerHTML = opts.saveBtnHtml;
        var bc = document.getElementById('btn-cancel');
        if (bc) bc.style.display = 'none';
    };

    window.editRecord = function(btn) {
        var row = btn.closest('tr');
        if (!row) return;
        row.querySelectorAll('.view-mode').forEach(function(el) { el.style.display = 'none'; });
        row.querySelectorAll('.edit-mode').forEach(function(el) { el.style.display = ''; });
        row.querySelectorAll('.editable').forEach(function(el) {
            var input = el.querySelector('input, select, textarea');
            if (input) input.value = el.getAttribute('data-val') || el.innerText.trim();
        });
        row.classList.add('editing');
    };

    window.cancelEdit = function(btn) {
        var row = btn && btn.closest ? btn.closest('tr') : null;
        if (row) {
            row.querySelectorAll('.view-mode').forEach(function(el) { el.style.display = ''; });
            row.querySelectorAll('.edit-mode').forEach(function(el) { el.style.display = 'none'; });
            row.classList.remove('editing');
        } else {
            crudCancelEdit('billForm', {});
        }
    };

    window.saveRecord = function(btn, url) {
        var row = btn.closest('tr');
        if (!row) return;
        var data = { csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value };
        row.querySelectorAll('.editable').forEach(function(el) {
            var input = el.querySelector('input, select, textarea');
            var field = el.getAttribute('data-field') || input.name || input.id;
            if (field && input) data[field] = input.value;
        });
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
            body: new URLSearchParams(data)
        }).then(function(r) { return r.json(); }).then(function(resp) {
            if (resp.success) {
                row.querySelectorAll('.editable').forEach(function(el) {
                    var input = el.querySelector('input, select, textarea');
                    if (input) el.innerText = input.value;
                });
                window.cancelEdit(btn);
            } else {
                alert('Save failed: ' + (resp.error || 'Unknown error'));
            }
        }).catch(function(err) { alert('Network error: ' + err.message); });
    };

    window.deleteRecord = function(btn, url, confirmMsg) {
        if (!confirm(confirmMsg || 'Are you sure you want to delete this record?')) return;
        var row = btn.closest('tr');
        var data = { csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value };
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
            body: new URLSearchParams(data)
        }).then(function(r) { return r.json(); }).then(function(resp) {
            if (resp.success) { if (row) row.remove(); }
            else { alert('Delete failed: ' + (resp.error || 'Unknown error')); }
        }).catch(function(err) { alert('Network error: ' + err.message); });
    };

    window.filterTable = function(input) {
        var q = input.value.toLowerCase();
        var table = input.closest('.glass-card').querySelector('table') || input.closest('table');
        if (!table) return;
        table.querySelectorAll('tbody tr').forEach(function(row) {
            if (row.classList.contains('no-data-row')) return;
            var match = Array.from(row.querySelectorAll('td')).some(function(td) { return td.innerText.toLowerCase().includes(q); });
            row.style.display = match ? '' : 'none';
        });
    };
})();
