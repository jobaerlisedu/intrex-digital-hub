# Firestore is the source of truth for all data including users.
# Django User table is a read-only cache populated on successful auth.
# No Django->Firestore sync signals needed.