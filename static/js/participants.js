// filepath: /Users/oleksii/Documents/PROJECTS/counter_for_run/static/js/participants.js
document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const registrationForm = document.getElementById('registration-form');
    const participantIdInput = document.getElementById('participant-id');
    const numberInput = document.getElementById('participant-number');
    const firstNameInput = document.getElementById('participant-first-name');
    const lastNameInput = document.getElementById('participant-last-name');
    const facultySelect = document.getElementById('participant-faculty');
    const typeSelect = document.getElementById('participant-type');
    const submitBtn = document.getElementById('submit-btn');
    const resetFormBtn = document.getElementById('reset-form-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    
    // Registration control buttons
    const toggleRegistrationBtn = document.getElementById('toggle-registration-btn');
    const startEventBtn = document.getElementById('start-event-btn');
    const registrationStatus = document.getElementById('registration-status');
    
    // Initial form state
    let isEditMode = false;
    
    // Registration form submission
    registrationForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        
        if (isEditMode) {
            // Update participant
            formData.append('id', participantIdInput.value);
            formData.append('first_name', firstNameInput.value);
            formData.append('last_name', lastNameInput.value);
            formData.append('faculty', facultySelect.value);
            formData.append('participant_type', typeSelect.value);
            
            fetch('/update_participant', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showSuccessMessage('Учасника оновлено');
                    resetForm();
                    location.reload(); // Reload to see changes
                }
            })
            .catch(error => {
                console.error('Error updating participant:', error);
                showErrorMessage('Помилка при оновленні учасника');
            });
        } else {
            // Register new participant
            formData.append('number', numberInput.value);
            formData.append('first_name', firstNameInput.value);
            formData.append('last_name', lastNameInput.value);
            formData.append('faculty', facultySelect.value);
            formData.append('participant_type', typeSelect.value);
            
            fetch('/register_participant', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showSuccessMessage('Учасника зареєстровано');
                    resetForm();
                    location.reload(); // Reload to see changes
                } else {
                    showErrorMessage(data.message || 'Помилка при реєстрації учасника');
                }
            })
            .catch(error => {
                console.error('Error registering participant:', error);
                showErrorMessage('Помилка при реєстрації учасника');
            });
        }
    });
    
    // Reset form button
    resetFormBtn.addEventListener('click', function() {
        resetForm();
    });
    
    // Cancel edit button
    cancelEditBtn.addEventListener('click', function() {
        resetForm();
    });
    
    // Edit participant buttons
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            const row = document.querySelector(`tr[data-id="${id}"]`);
            
            if (row) {
                const cells = row.cells;
                
                // Switch to edit mode
                isEditMode = true;
                
                // Set participant ID
                participantIdInput.value = id;
                
                // Fill form with participant data
                numberInput.value = cells[1].textContent.trim();
                firstNameInput.value = cells[2].textContent.trim();
                lastNameInput.value = cells[3].textContent.trim();
                
                // Find and select the faculty
                const faculty = cells[4].textContent.trim();
                Array.from(facultySelect.options).forEach(option => {
                    if (option.textContent === faculty) {
                        option.selected = true;
                    }
                });
                
                // Find and select the participant type
                const type = cells[5].textContent.trim();
                Array.from(typeSelect.options).forEach(option => {
                    if (option.textContent.includes(type)) {
                        option.selected = true;
                    }
                });
                
                // Disable number input in edit mode
                numberInput.disabled = true;
                
                // Update form appearance
                submitBtn.textContent = 'Оновити';
                submitBtn.className = 'btn btn-success';
                cancelEditBtn.classList.remove('d-none');
                
                // Scroll to form
                registrationForm.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Delete participant buttons
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            const row = document.querySelector(`tr[data-id="${id}"]`);
            
            if (row) {
                const number = row.cells[1].textContent.trim();
                const name = `${row.cells[2].textContent.trim()} ${row.cells[3].textContent.trim()}`;
                
                if (confirm(`Ви впевнені, що хочете видалити учасника #${number} (${name})?`)) {
                    fetch('/delete_participant', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ id: id })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            row.remove();
                            
                            // Update participants count
                            const participantsCount = document.getElementById('participants-count');
                            participantsCount.textContent = document.querySelectorAll('#participants-body tr').length;
                            
                            showSuccessMessage('Учасника видалено');
                        }
                    })
                    .catch(error => {
                        console.error('Error deleting participant:', error);
                        showErrorMessage('Помилка при видаленні учасника');
                    });
                }
            }
        });
    });
    
    // Toggle registration status
    if (toggleRegistrationBtn) {
        toggleRegistrationBtn.addEventListener('click', function() {
            fetch('/toggle_registration', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI based on new registration status
                    const isOpen = data.registration_open;
                    
                    toggleRegistrationBtn.textContent = isOpen ? 'Закрити реєстрацію' : 'Відкрити реєстрацію';
                    toggleRegistrationBtn.className = `btn ${isOpen ? 'btn-danger' : 'btn-success'}`;
                    
                    registrationStatus.textContent = `Реєстрація ${isOpen ? 'відкрита' : 'закрита'}`;
                    registrationStatus.className = `alert ${isOpen ? 'alert-success' : 'alert-danger'}`;
                    
                    // Enable/disable form inputs
                    const formInputs = registrationForm.querySelectorAll('input, select');
                    formInputs.forEach(input => {
                        input.disabled = !isOpen;
                    });
                    
                    submitBtn.disabled = !isOpen;
                }
            })
            .catch(error => console.error('Error toggling registration:', error));
        });
    }
    
    // Start event button
    if (startEventBtn) {
        startEventBtn.addEventListener('click', function() {
            if (confirm('Ви впевнені, що хочете розпочати забіг? Це закриє реєстрацію учасників.')) {
                fetch('/start_event', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = '/';
                    }
                })
                .catch(error => console.error('Error starting event:', error));
            }
        });
    }
    
    // Helper functions
    function resetForm() {
        // Clear form
        registrationForm.reset();
        participantIdInput.value = '';
        
        // Reset form state
        isEditMode = false;
        
        // Enable number input
        numberInput.disabled = false;
        
        // Reset form appearance
        submitBtn.textContent = 'Зареєструвати';
        submitBtn.className = 'btn btn-primary';
        cancelEditBtn.classList.add('d-none');
    }
    
    function showSuccessMessage(message) {
        alert(message);
    }
    
    function showErrorMessage(message) {
        alert(message);
    }
});