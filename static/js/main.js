document.addEventListener('DOMContentLoaded', function() {
    // Initial data load
    updateStandings();
    updateParticipantRanking();
    
    // Set interval for periodic updates
    setInterval(updateStandings, 5000);
    setInterval(updateParticipantRanking, 5000);
    
    // Initialize the confirmation modal
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    
    // Reset database button
    const resetDbBtn = document.getElementById('reset-db-btn');
    if (resetDbBtn) {
        resetDbBtn.addEventListener('click', function() {
            document.getElementById('confirmModalBody').textContent = 'Ви впевнені, що хочете скинути базу даних? Всі дані будуть втрачені.';
            document.getElementById('confirmModalBtn').setAttribute('data-action', 'reset-database');
            confirmModal.show();
        });
    }
    
    // Modal confirmation button
    document.getElementById('confirmModalBtn').addEventListener('click', function() {
        const action = this.getAttribute('data-action');
        
        if (action === 'reset-database') {
            resetDatabase();
        }
        
        confirmModal.hide();
    });
    
    // Faculty-specific buttons for adding laps
    document.querySelectorAll('.add-faculty-lap').forEach(button => {
        button.addEventListener('click', function() {
            const faculty = this.getAttribute('data-faculty');
            const selectElement = document.querySelector(`.faculty-type-select[data-faculty="${faculty}"]`);
            const participantType = selectElement.value;
            
            addFacultyLap(faculty, participantType, this);
        });
    });
    
    // Faculty-specific buttons for subtracting laps
    document.querySelectorAll('.subtract-faculty-lap').forEach(button => {
        button.addEventListener('click', function() {
            const faculty = this.getAttribute('data-faculty');
            const selectElement = document.querySelector(`.faculty-type-select[data-faculty="${faculty}"]`);
            const participantType = selectElement.value;
            
            // Show confirmation dialog
            document.getElementById('confirmModalBody').textContent = `Ви впевнені, що хочете відняти коло для факультету "${faculty}"?`;
            document.getElementById('confirmModalBtn').setAttribute('data-action', 'subtract-faculty-lap');
            document.getElementById('confirmModalBtn').setAttribute('data-faculty', faculty);
            document.getElementById('confirmModalBtn').setAttribute('data-type', participantType);
            confirmModal.show();
            
            // Add event listener for confirmation
            document.getElementById('confirmModalBtn').addEventListener('click', function(e) {
                if (this.getAttribute('data-action') === 'subtract-faculty-lap') {
                    const faculty = this.getAttribute('data-faculty');
                    const participantType = this.getAttribute('data-type');
                    
                    subtractFacultyLap(faculty, participantType);
                    
                    // Remove these attributes after use
                    this.removeAttribute('data-faculty');
                    this.removeAttribute('data-type');
                    this.removeAttribute('data-action');
                    
                    // Remove this specific event listener to avoid multiple bindings
                    e.target.removeEventListener(e.type, arguments.callee);
                }
            });
        });
    });
    
    // Participant number input event - lookup participant info
    const participantNumberInput = document.getElementById('participant-number');
    if (participantNumberInput) {
        participantNumberInput.addEventListener('blur', function() {
            const participantNumber = this.value.trim();
            
            if (participantNumber) {
                lookupParticipantInfo(participantNumber);
            }
        });
    }
    
    // Add lap button for specific participant
    const addLapBtn = document.getElementById('add-lap-btn');
    if (addLapBtn) {
        addLapBtn.addEventListener('click', function() {
            const participantNumber = document.getElementById('participant-number').value.trim();
            const participantType = document.getElementById('participant-type').value;
            const faculty = document.getElementById('participant-faculty').value;
            
            if (!participantNumber) {
                alert('Будь ласка, введіть номер учасника');
                return;
            }
            
            if (!faculty) {
                alert('Не вдалося визначити факультет учасника');
                return;
            }
            
            addLap(faculty, participantType, participantNumber);
            
            // Show feedback
            const originalText = this.textContent;
            this.textContent = '✓ Коло додано!';
            this.disabled = true;
            
            setTimeout(() => {
                this.textContent = originalText;
                this.disabled = false;
            }, 1000);
        });
    }
    
    // Subtract lap button for specific participant
    const subtractLapBtn = document.getElementById('subtract-lap-btn');
    if (subtractLapBtn) {
        subtractLapBtn.addEventListener('click', function() {
            const participantNumber = document.getElementById('participant-number').value.trim();
            const participantType = document.getElementById('participant-type').value;
            const faculty = document.getElementById('participant-faculty').value;
            
            if (!participantNumber) {
                alert('Будь ласка, введіть номер учасника');
                return;
            }
            
            if (!faculty) {
                alert('Не вдалося визначити факультет учасника');
                return;
            }
            
            subtractLap(faculty, participantType, participantNumber);
            
            // Show feedback will be handled in the subtractLap function
        });
    }
    
    // Donation form submission
    document.getElementById('donation-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const faculty = document.getElementById('donation-faculty').value;
        const amount = document.getElementById('donation-amount').value;
        const comment = document.getElementById('donation-comment').value;
        
        if (faculty && amount > 0) {
            addDonation(faculty, amount, comment);
        }
    });
    
    // Subtract donation button click
    document.getElementById('subtract-donation').addEventListener('click', function() {
        const faculty = document.getElementById('donation-faculty').value;
        const amount = document.getElementById('donation-amount').value;
        
        if (faculty && amount > 0) {
            subtractDonation(faculty, amount);
        } else {
            alert('Будь ласка, виберіть факультет та вкажіть суму');
        }
    });
});

// Function to update standings table
function updateStandings() {
    fetch('/get_standings')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('standings-body');
            
            // Store current order to detect changes
            const oldOrder = Array.from(tableBody.querySelectorAll('tr'))
                .map(row => row.getAttribute('data-faculty'));
            
            // Clear current content
            tableBody.innerHTML = '';
            
            // Add new rows
            data.forEach((faculty, index) => {
                const row = document.createElement('tr');
                row.setAttribute('data-faculty', faculty.faculty);
                row.classList.add('animated-row');
                
                // Set background color with low opacity
                row.style.backgroundColor = `${faculty.color}10`;
                
                row.innerHTML = `
                    <td>${index + 1}</td>
                    <td>
                        <span class="faculty-indicator" style="background-color: ${faculty.color}"></span>
                        ${faculty.faculty}
                    </td>
                    <td>${faculty.student_laps}</td>
                    <td>${faculty.employee_laps || 0}</td>
                    <td>${faculty.teacher_laps}</td>
                    <td>${faculty.dean_laps}</td>
                    <td>${faculty.donations.toFixed(2)} грн</td>
                    <td><strong>${faculty.total_points}</strong></td>
                `;
                tableBody.appendChild(row);
                
                // Highlight if position changed
                const oldPosition = oldOrder.indexOf(faculty.faculty);
                if (oldPosition !== -1 && oldPosition !== index) {
                    row.classList.add('highlight');
                }
            });
        })
        .catch(error => console.error('Error fetching standings:', error));
}

// Function to update participant ranking
function updateParticipantRanking() {
    fetch('/get_participant_ranking')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('participant-body');
            
            // Store current top participants to detect changes
            const oldTop = Array.from(tableBody.querySelectorAll('tr'))
                .map(row => row.getAttribute('data-participant'));
            
            // Clear current content
            tableBody.innerHTML = '';
            
            if (data.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="7" class="text-center">Поки немає результатів</td>';
                tableBody.appendChild(row);
                return;
            }
            
            // Add new rows
            data.forEach(participant => {
                const row = document.createElement('tr');
                row.setAttribute('data-participant', `${participant.participant_number}-${participant.faculty}`);
                row.classList.add('animated-row');
                
                // Set background color with low opacity
                row.style.backgroundColor = `${participant.color}10`;
                
                // Format name
                const participantName = `${participant.first_name || ''} ${participant.last_name || ''}`.trim();
                const displayName = participantName || 'Невідомий учасник';
                
                // Format faculty - just use first word or color indicator only
                const facultyShort = participant.faculty.split(' ')[0];
                
                row.innerHTML = `
                    <td>${participant.rank}</td>
                    <td>${participant.participant_number}</td>
                    <td>${displayName}</td>
                    <td>${participant.participant_type}</td>
                    <td>
                        <span class="faculty-indicator" style="background-color: ${participant.color}"></span>
                        ${facultyShort}
                    </td>
                    <td>${participant.laps} км</td>
                    <td><strong>+${participant.points}</strong></td>
                `;
                tableBody.appendChild(row);
                
                // Highlight new entries in top 10
                if (participant.rank <= 10 && !oldTop.includes(`${participant.participant_number}-${participant.faculty}`)) {
                    row.classList.add('highlight');
                }
            });
        })
        .catch(error => console.error('Error fetching participant ranking:', error));
}

// Function to reset database
function resetDatabase() {
    fetch('/reset_database', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('База даних успішно скинута. Сторінка буде перезавантажена.');
            window.location.href = '/participants';  // Redirect to participants page to add new participants
        } else {
            alert('Помилка при скиданні бази даних: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error resetting database:', error);
        alert('Помилка при скиданні бази даних');
    });
}

// Function to add a lap for a specific faculty (without participant)
function addFacultyLap(faculty, participantType, buttonElement) {
    fetch('/add_faculty_lap', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            faculty: faculty,
            participantType: participantType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update standings and participant ranking immediately
            updateStandings();
            updateParticipantRanking();
            
            // Show feedback
            const originalText = buttonElement.textContent;
            buttonElement.textContent = '✓ Додано!';
            buttonElement.disabled = true;
            
            setTimeout(() => {
                buttonElement.textContent = originalText;
                buttonElement.disabled = false;
            }, 1000);
        }
    })
    .catch(error => console.error('Error adding faculty lap:', error));
}

// Function to subtract a lap for a specific faculty (without participant)
function subtractFacultyLap(faculty, participantType) {
    fetch('/subtract_faculty_lap', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            faculty: faculty,
            participantType: participantType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update standings and participant ranking immediately
            updateStandings();
            updateParticipantRanking();
            
            // Show feedback via alert
            alert(`Коло віднято для факультету "${faculty}"`);
        } else {
            alert(data.message || 'Немає кіл для віднімання');
        }
    })
    .catch(error => {
        console.error('Error subtracting faculty lap:', error);
        alert('Помилка при відніманні кола для факультету');
    });
}

// Function to add a lap for a specific participant
function addLap(faculty, participantType, participantNumber) {
    fetch('/add_lap', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            faculty: faculty,
            participantType: participantType,
            participantNumber: participantNumber
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update standings and participant ranking immediately
            updateStandings();
            updateParticipantRanking();
        }
    })
    .catch(error => console.error('Error adding lap:', error));
}

// Function to subtract a lap for a specific participant
function subtractLap(faculty, participantType, participantNumber) {
    if (!confirm(`Ви впевнені, що хочете відняти коло учасника #${participantNumber} для факультету "${faculty}"?`)) {
        return;
    }
    
    fetch('/subtract_lap', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            faculty: faculty,
            participantType: participantType,
            participantNumber: participantNumber
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update standings and participant ranking immediately
            updateStandings();
            updateParticipantRanking();
            
            // Show feedback
            alert(`Коло віднято для учасника #${participantNumber}`);
        } else {
            alert(data.message || 'Немає кіл для віднімання');
        }
    })
    .catch(error => {
        console.error('Error subtracting lap:', error);
        alert('Помилка при відніманні кола');
    });
}

// Function to add a donation
function addDonation(faculty, amount, comment) {
    if (!faculty) {
        alert('Будь ласка, виберіть факультет');
        return;
    }
    
    if (!amount || amount <= 0) {
        alert('Будь ласка, введіть коректну суму');
        return;
    }
    
    const formData = new FormData();
    formData.append('faculty', faculty);
    formData.append('amount', amount);
    formData.append('comment', comment || '');
    
    fetch('/add_donation', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update standings immediately
            updateStandings();
            
            // Reset form
            document.getElementById('donation-form').reset();
            
            // Show feedback
            const submitButton = document.querySelector('#donation-form button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.textContent = '✓ Донат додано!';
            submitButton.className = 'btn btn-success';
            
            setTimeout(() => {
                submitButton.textContent = originalText;
                submitButton.className = 'btn btn-primary';
            }, 2000);
        } else {
            alert(data.message || 'Помилка при додаванні донату');
        }
    })
    .catch(error => {
        console.error('Error adding donation:', error);
        alert('Помилка при додаванні донату');
    });
}

// Function to subtract a donation
function subtractDonation(faculty, amount) {
    if (!confirm(`Ви впевнені, що хочете відняти донат у розмірі ${amount} грн для факультету "${faculty}"?`)) {
        return;
    }
    
    const formData = new FormData();
    formData.append('faculty', faculty);
    formData.append('amount', amount);
    
    fetch('/subtract_donation', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update standings immediately
            updateStandings();
            
            // Show feedback
            const submitButton = document.getElementById('subtract-donation');
            const originalText = submitButton.textContent;
            submitButton.textContent = '✓ Донат віднято!';
            submitButton.className = 'btn btn-success';
            
            setTimeout(() => {
                submitButton.textContent = originalText;
                submitButton.className = 'btn btn-outline-danger';
            }, 2000);
            
            // Reset form
            document.getElementById('donation-form').reset();
        } else {
            alert(data.message || 'Немає донатів для віднімання');
        }
    })
    .catch(error => {
        console.error('Error subtracting donation:', error);
        alert('Помилка при відніманні донату');
    });
}

// Function to lookup participant info
function lookupParticipantInfo(participantNumber) {
    fetch(`/lookup_participant_info?participantNumber=${participantNumber}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Set values in form
                const facultySelect = document.getElementById('participant-faculty');
                const typeSelect = document.getElementById('participant-type');
                
                facultySelect.value = data.faculty;
                typeSelect.value = data.participantType;
                
                // Enable buttons
                document.getElementById('add-lap-btn').disabled = false;
                document.getElementById('subtract-lap-btn').disabled = false;
                
                // Show success indicator
                const participantNumberInput = document.getElementById('participant-number');
                participantNumberInput.classList.add('is-valid');
                participantNumberInput.classList.remove('is-invalid');
            } else {
                // Show not found message
                const participantNumberInput = document.getElementById('participant-number');
                participantNumberInput.classList.add('is-invalid');
                participantNumberInput.classList.remove('is-valid');
                
                // Reset and disable fields
                document.getElementById('participant-faculty').value = "";
                document.getElementById('participant-type').value = "";
                
                // Disable buttons
                document.getElementById('add-lap-btn').disabled = true;
                document.getElementById('subtract-lap-btn').disabled = true;
            }
        })
        .catch(error => {
            console.error('Error looking up participant info:', error);
            alert('Помилка при пошуку інформації про учасника');
        });
}
