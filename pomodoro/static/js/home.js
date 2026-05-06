// AJAX function for real-time tag updates
function updateTagsViaAJAX(taskId, tags) {
    const formData = new FormData();
    formData.append('tags', tags);
    
    fetch(`/update-tags-ajax/${taskId}`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            console.error('Failed to update tags:', response.status);
            // Optionally show user feedback
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('Tags updated successfully');
            // Update visual tag display immediately
            updateTagDisplay(taskId, tags);
        } else {
            console.error('Server error updating tags:', data.error);
        }
    })
    .catch(error => {
        console.error('Network error updating tags:', error);
    });
}

// Function to update the visual tag display for a task
function updateTagDisplay(taskId, tags) {
    // Find the task element
    const taskForm = document.querySelector(`.tag-form[data-task-id="${taskId}"]`);
    if (!taskForm) return;
    
    // Find the tag display container (should be before the form)
    const taskItem = taskForm.closest('.task-item');
    if (!taskItem) return;
    
    const tagDisplay = taskItem.querySelector('.task-tags-display');
    if (!tagDisplay) return;
    
    // Clear existing tag dots
    tagDisplay.innerHTML = '';
    
    // Add new tag dots based on the updated tags
    if (tags) {
        const colors = tags.split(',').filter(color => color.trim());
        colors.forEach(color => {
            const colorClass = getColorClass(color.trim());
            if (colorClass) {
                const tagDot = document.createElement('span');
                tagDot.className = `tag-dot ${colorClass}`;
                tagDot.title = color.trim();
                tagDisplay.appendChild(tagDot);
            }
        });
    }
}

// Helper function to convert hex color to CSS class
function getColorClass(hexColor) {
    const colorMap = {
        '#ff5252': 'tag-red',
        '#ff9800': 'tag-orange', 
        '#ffeb3b': 'tag-yellow',
        '#4caf50': 'tag-green',
        '#00bcd4': 'tag-cyan',
        '#3f51b5': 'tag-indigo',
        '#9c27b0': 'tag-purple',
        '#795548': 'tag-brown'
    };
    return colorMap[hexColor] || '';
}

// Home page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('Home page loaded');

    // Tag menu logic
    const closeAllTagMenus = () => {
        document.querySelectorAll('.tag-menu').forEach(menu => {
            menu.classList.remove('open');
            menu.setAttribute('aria-hidden', 'true');
            // Move menu back to its original form
            const originalForm = menu.dataset.originalForm;
            if (originalForm) {
                const form = document.querySelector(`.tag-form[data-form-id="${originalForm}"]`);
                if (form) {
                    form.appendChild(menu);
                }
            }
        });
    };

    // Open/close tag menu
    document.querySelectorAll('.tag-form').forEach((form, index) => {
        const btn = form.querySelector('.tag-btn');
        const menu = form.querySelector('.tag-menu');
        const hiddenInput = form.querySelector('input[name="tags"]');

        // Add unique ID to form for tracking
        form.setAttribute('data-form-id', `form-${index}`);
        menu.setAttribute('data-original-form', `form-${index}`);

        const presetButtons = Array.from(form.querySelectorAll('.color-choice'));

        // Initialize selected state from hidden input
        const initial = (hiddenInput?.value || '').split(',').filter(Boolean);
        presetButtons.forEach(b => {
            if (initial.includes(b.dataset.color)) b.classList.add('selected');
        });

        btn?.addEventListener('click', (e) => {
            e.preventDefault();
            const isOpen = menu.classList.contains('open');
            closeAllTagMenus();
            if (!isOpen) {
                // Move menu to body and position it
                document.body.appendChild(menu);
                
                // Position menu to the left of the button
                const rect = btn.getBoundingClientRect();
                menu.style.position = 'fixed';
                menu.style.top = `${rect.bottom + 6}px`;
                menu.style.right = 'auto';
                menu.style.left = `${rect.left - 180}px`; // Position 180px to the left (menu width + padding)
                
                // If menu would go off-screen left, adjust position
                if (rect.left - 180 < 10) {
                    menu.style.left = '10px';
                    menu.style.top = `${rect.bottom + 6}px`;
                }
                
                menu.classList.add('open');
                menu.setAttribute('aria-hidden', 'false');
            }
        });

        // Select/deselect colors with auto-apply
        presetButtons.forEach(b => {
            b.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation(); // Prevent event bubbling to avoid menu closure
                b.classList.toggle('selected');
                
                // Auto-apply: update hidden input and save immediately
                const colors = presetButtons.filter(btn => btn.classList.contains('selected')).map(btn => btn.dataset.color);
                if (hiddenInput) {
                    hiddenInput.value = colors.join(',');
                    // Trigger AJAX update
                    updateTagsViaAJAX(form.dataset.taskId, colors.join(','));
                }
            });
        });

        // Clear with auto-apply
        form.querySelector('.tag-clear')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation(); // Prevent event bubbling to avoid menu closure
            presetButtons.forEach(b => b.classList.remove('selected'));
            
            // Auto-apply: clear hidden input and save immediately
            if (hiddenInput) {
                hiddenInput.value = '';
                // Trigger AJAX update
                updateTagsViaAJAX(form.dataset.taskId, '');
            }
        });

        // Settings button - open tag settings modal
        const settingsBtn = form.querySelector('.tag-settings-btn');
        console.log('Settings button found:', settingsBtn);
        if (settingsBtn) {
            settingsBtn.addEventListener('click', (e) => {
                console.log('Settings button clicked!');
                e.preventDefault();
                e.stopPropagation(); // Prevent event bubbling to avoid menu closure
                openTagSettingsModal();
            });
        } else {
            console.log('Settings button not found in form:', form);
        }

        // Apply -> set hidden input and submit form
        form.querySelector('.tag-apply')?.addEventListener('click', (e) => {
            // allow normal submit, but first set value
            const colors = presetButtons.filter(b => b.classList.contains('selected')).map(b => b.dataset.color);
            if (hiddenInput) hiddenInput.value = colors.join(',');
            closeAllTagMenus();
        });
    });

    // Close menus on outside click
    document.addEventListener('click', (e) => {
        const isTagForm = e.target.closest?.('.tag-form');
        if (!isTagForm) closeAllTagMenus();
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeAllTagMenus();
    });

    // Event delegation for settings buttons (backup method)
    document.addEventListener('click', (e) => {
        if (e.target.closest('.tag-settings-btn')) {
            console.log('Settings button clicked via delegation!');
            e.preventDefault();
            e.stopPropagation();
            openTagSettingsModal();
        }
    });

    // Task sorting functionality
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            const sortType = e.target.value;
            sortTasks(sortType);
        });
    }
});

// Tag Settings Modal Functions
function openTagSettingsModal() {
    console.log('openTagSettingsModal() called');
    const modal = document.getElementById('tagSettingsModal');
    console.log('Modal element found:', modal);
    
    if (!modal) {
        console.error('Tag settings modal not found!');
        return;
    }
    
    console.log('Loading user tags...');
    // Load user tags and populate modal
    loadUserTags().then(tags => {
        console.log('User tags loaded:', tags);
        populateTagList(tags);
        
        // Show modal
        modal.classList.add('show');
        modal.setAttribute('aria-hidden', 'false');
        
        console.log('Modal should now be visible');
        console.log('Modal classes:', modal.className);
        
        // Setup event listeners
        setupTagSettingsListeners();
    }).catch(error => {
        console.error('Error in openTagSettingsModal:', error);
    });
}

function closeTagSettingsModal() {
    const modal = document.getElementById('tagSettingsModal');
    if (!modal) return;
    
    modal.classList.remove('show');
    modal.setAttribute('aria-hidden', 'true');
}

function loadUserTags() {
    return fetch('/api/tags', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            return data.tags;
        } else {
            console.error('Failed to load tags:', data.error);
            return [];
        }
    })
    .catch(error => {
        console.error('Error loading tags:', error);
        return [];
    });
}

function populateTagList(tags) {
    const tagList = document.getElementById('tagList');
    if (!tagList) return;
    
    tagList.innerHTML = '';
    
    if (tags.length === 0) {
        tagList.innerHTML = '<p class="no-tags">No custom tags yet. Add your first tag below!</p>';
        return;
    }
    
    tags.forEach(tag => {
        const tagItem = document.createElement('div');
        tagItem.className = 'tag-item';
        tagItem.dataset.tagId = tag.id;
        tagItem.dataset.tagColor = tag.color_hex;
        
        tagItem.innerHTML = `
            <div class="tag-item-info">
                <div class="tag-preview" style="background-color: ${tag.color_hex}"></div>
                <div>
                    <div class="tag-name">${tag.color_name || 'Unnamed Tag'}</div>
                    <div class="tag-color-hex">${tag.color_hex}</div>
                </div>
            </div>
            <div class="tag-item-actions">
                <button type="button" class="tag-edit-btn" data-tag-id="${tag.id}">Edit</button>
                <button type="button" class="tag-delete-btn" data-tag-id="${tag.id}">Delete</button>
            </div>
        `;
        
        tagList.appendChild(tagItem);
    });
}

function setupTagSettingsListeners() {
    // Close modal buttons
    document.querySelectorAll('#tagSettingsModal .modal-close, #tagSettingsModal .modal-cancel').forEach(btn => {
        btn.addEventListener('click', closeTagSettingsModal);
    });
    
    // Close on backdrop click
    document.querySelector('#tagSettingsModal .modal-backdrop')?.addEventListener('click', closeTagSettingsModal);
    
    // Add new tag button
    document.getElementById('addCustomTag')?.addEventListener('click', addNewTag);
    
    // Edit and delete buttons
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('tag-edit-btn')) {
            editTag(e.target.dataset.tagId);
        } else if (e.target.classList.contains('tag-delete-btn')) {
            deleteTag(e.target.dataset.tagId);
        }
    });
}

function addNewTag() {
    const colorInput = document.getElementById('newTagColor');
    const nameInput = document.getElementById('newTagName');
    
    const color = colorInput.value;
    const name = nameInput.value.trim();
    
    if (!color) {
        alert('Please select a color');
        return;
    }
    
    const formData = new FormData();
    formData.append('color_hex', color);
    formData.append('color_name', name);
    
    fetch('/api/tags', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Clear form
            colorInput.value = '#000000';
            nameInput.value = '';
            
            // Reload tags
            loadUserTags().then(tags => populateTagList(tags));
        } else {
            alert('Failed to add tag: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error adding tag:', error);
        alert('Failed to add tag');
    });
}

function editTag(tagId) {
    // TODO: Implement edit functionality
    console.log('Edit tag:', tagId);
    alert('Edit functionality will be implemented in the next step');
}

function deleteTag(tagId) {
    // Use the existing delete confirmation modal
    const deleteModal = document.getElementById('deleteModal');
    const taskContent = document.getElementById('taskContent');
    const confirmBtn = deleteModal.querySelector('.modal-confirm');
    
    // Update modal content for tag deletion
    taskContent.textContent = `this tag`;
    
    // Find the tag element to get its info
    const tagElement = document.querySelector(`[data-tag-id="${tagId}"]`);
    const tagName = tagElement?.querySelector('.tag-name')?.textContent || 'Unknown tag';
    const tagColor = tagElement?.dataset.tagColor || '';
    
    // Update modal title and message
    const modalTitle = document.getElementById('modalTitle');
    modalTitle.textContent = 'Confirm Delete Tag';
    
    // Store tag info for confirmation
    deleteModal.dataset.tagId = tagId;
    deleteModal.dataset.tagColor = tagColor;
    
    // Update confirm button handler for tag deletion
    confirmBtn.onclick = () => {
        fetch(`/api/tags/${tagId}`, {
            method: 'DELETE',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Hide delete modal
                deleteModal.classList.remove('show');
                deleteModal.setAttribute('aria-hidden', 'true');
                
                // Reload tags in settings modal
                loadUserTags().then(tags => populateTagList(tags));
                
                // Show success message
                console.log('Tag deleted successfully');
            } else {
                alert('Failed to delete tag: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error deleting tag:', error);
            alert('Failed to delete tag');
        });
    };
    
    // Show the delete modal
    deleteModal.classList.add('show');
    deleteModal.setAttribute('aria-hidden', 'false');
}

// Task Sorting Functions
function sortTasks(sortType) {
    const taskList = document.querySelector('.task-list');
    if (!taskList) return;
    
    const tasks = Array.from(taskList.children);
    let sortedTasks;
    
    switch(sortType) {
        case 'tag-color':
            sortedTasks = sortByTagColor(tasks);
            break;
        case 'alphabetical-az':
            sortedTasks = sortAlphabetically(tasks, 'asc');
            break;
        case 'alphabetical-za':
            sortedTasks = sortAlphabetically(tasks, 'desc');
            break;
        case 'tag-color-alpha':
            sortedTasks = sortByTagColorThenAlpha(tasks);
            break;
        default:
            return; // Keep current order
    }
    
    reorderTasks(taskList, sortedTasks);
}

function sortByTagColor(tasks) {
    return tasks.sort((a, b) => {
        const colorA = getPrimaryTagColor(a);
        const colorB = getPrimaryTagColor(b);
        
        // Tasks without tags go to the end
        if (!colorA && !colorB) return 0;
        if (!colorA) return 1;
        if (!colorB) return -1;
        
        // Sort by hex color value
        return colorA.localeCompare(colorB);
    });
}

function sortAlphabetically(tasks, direction) {
    return tasks.sort((a, b) => {
        const textA = getTaskContent(a).toLowerCase();
        const textB = getTaskContent(b).toLowerCase();
        return direction === 'asc' ? 
            textA.localeCompare(textB) : 
            textB.localeCompare(textA);
    });
}

function sortByTagColorThenAlpha(tasks) {
    return tasks.sort((a, b) => {
        const colorA = getPrimaryTagColor(a);
        const colorB = getPrimaryTagColor(b);
        
        // First sort by tag color
        if (colorA && colorB) {
            const colorComparison = colorA.localeCompare(colorB);
            if (colorComparison !== 0) return colorComparison;
        }
        
        // If colors are the same or one has no color, sort alphabetically
        const textA = getTaskContent(a).toLowerCase();
        const textB = getTaskContent(b).toLowerCase();
        return textA.localeCompare(textB);
    });
}

function getPrimaryTagColor(taskElement) {
    // Get the first tag color from the task
    const tagDot = taskElement.querySelector('.tag-dot');
    if (!tagDot) return null;
    
    // Extract color from title attribute or computed style
    const color = tagDot.title || tagDot.style.backgroundColor;
    
    // Convert to hex format if needed
    if (color.startsWith('#')) return color.toLowerCase();
    
    // Handle rgb() format
    if (color.startsWith('rgb')) {
        const rgb = color.match(/\d+/g);
        if (rgb && rgb.length >= 3) {
            const hex = '#' + rgb.slice(0, 3).map(x => {
                const hex = parseInt(x).toString(16);
                return hex.length === 1 ? '0' + hex : hex;
            }).join('');
            return hex.toLowerCase();
        }
    }
    
    return color.toLowerCase();
}

function getTaskContent(taskElement) {
    // Get the task text content
    const contentElement = taskElement.querySelector('.task-content');
    return contentElement ? contentElement.textContent.trim() : '';
}

function reorderTasks(taskList, sortedTasks) {
    // Clear current tasks
    taskList.innerHTML = '';
    
    // Add sorted tasks back to the list
    sortedTasks.forEach(task => {
        taskList.appendChild(task);
    });
    
    // Update task positions in database if needed
    updateTaskPositions(sortedTasks);
}

function updateTaskPositions(sortedTasks) {
    // Optional: Update task positions in database
    // This would require an AJAX call to maintain sort order
    // For now, we'll just log it
    console.log('Task order updated:', sortedTasks.map((task, index) => ({
        position: index,
        content: getTaskContent(task),
        tags: Array.from(task.querySelectorAll('.tag-dot')).map(dot => dot.title)
    })));
}