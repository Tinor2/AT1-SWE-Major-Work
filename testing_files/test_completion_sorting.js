// Test script to verify completion sorting functionality
// This simulates the DOM structure and tests the sorting functions

// Mock DOM elements for testing
function createMockTaskElement(id, content, isCompleted, hasTags = false) {
    const taskElement = {
        classList: {
            contains: function(className) {
                if (className === 'completed') return isCompleted;
                return false;
            }
        },
        querySelector: function(selector) {
            if (selector.includes('toggle_task')) {
                return {
                    checked: isCompleted
                };
            }
            if (selector === '.task-content') {
                return {
                    textContent: content
                };
            }
            if (selector === '.tag-dot') {
                return hasTags ? { title: '#ff5252' } : null;
            }
            return null;
        },
        querySelectorAll: function(selector) {
            if (selector === '.tag-dot') {
                return hasTags ? [{ title: '#ff5252' }] : [];
            }
            return [];
        }
    };
    return taskElement;
}

// Copy the sorting functions from the actual code
function isTaskCompleted(taskElement) {
    // Check if the task is completed by looking for the checked checkbox in the toggle form
    const toggleCheckbox = taskElement.querySelector('form[action*="toggle_task"] input[type="checkbox"]');
    if (toggleCheckbox) {
        return toggleCheckbox.checked;
    }
    
    // Alternative: check if the task element has the 'completed' class
    return taskElement.classList.contains('completed') || 
           taskElement.querySelector('.task-item.completed') !== null;
}

function sortByCompletion(tasks, order) {
    return tasks.sort((a, b) => {
        const isCompletedA = isTaskCompleted(a);
        const isCompletedB = isTaskCompleted(b);
        
        if (order === 'incomplete-first') {
            // Incomplete tasks first (0 comes before 1)
            if (isCompletedA && !isCompletedB) return 1;
            if (!isCompletedA && isCompletedB) return -1;
            return 0; // Same completion status, keep original order
        } else if (order === 'complete-first') {
            // Complete tasks first (0 comes before 1)
            if (!isCompletedA && isCompletedB) return 1;
            if (isCompletedA && !isCompletedB) return -1;
            return 0; // Same completion status, keep original order
        }
        return 0;
    });
}

// Test the sorting functionality
function testCompletionSorting() {
    console.log('Testing completion sorting functionality...');
    
    // Create mock tasks
    const tasks = [
        createMockTaskElement(1, 'Task 1', false),    // incomplete
        createMockTaskElement(2, 'Task 2', true),     // complete
        createMockTaskElement(3, 'Task 3', false),    // incomplete
        createMockTaskElement(4, 'Task 4', true),     // complete
        createMockTaskElement(5, 'Task 5', false)     // incomplete
    ];
    
    console.log('Original order:');
    tasks.forEach((task, index) => {
        console.log(`${index + 1}. Task ${index + 1} - Completed: ${isTaskCompleted(task)}`);
    });
    
    // Test incomplete-first sorting
    console.log('\nTesting "Incomplete First" sorting:');
    const incompleteFirst = sortByCompletion([...tasks], 'incomplete-first');
    incompleteFirst.forEach((task, index) => {
        console.log(`${index + 1}. Task ${task.id} - Completed: ${isTaskCompleted(task)}`);
    });
    
    // Test complete-first sorting
    console.log('\nTesting "Complete First" sorting:');
    const completeFirst = sortByCompletion([...tasks], 'complete-first');
    completeFirst.forEach((task, index) => {
        console.log(`${index + 1}. Task ${task.id} - Completed: ${isTaskCompleted(task)}`);
    });
    
    // Verify results
    console.log('\nVerification:');
    
    // Check incomplete-first: first 3 should be incomplete, last 2 should be complete
    const incompleteFirstCorrect = incompleteFirst.slice(0, 3).every(task => !isTaskCompleted(task)) &&
                                  incompleteFirst.slice(3).every(task => isTaskCompleted(task));
    console.log(`Incomplete-first sorting correct: ${incompleteFirstCorrect}`);
    
    // Check complete-first: first 2 should be complete, last 3 should be incomplete
    const completeFirstCorrect = completeFirst.slice(0, 2).every(task => isTaskCompleted(task)) &&
                                 completeFirst.slice(2).every(task => !isTaskCompleted(task));
    console.log(`Complete-first sorting correct: ${completeFirstCorrect}`);
    
    return incompleteFirstCorrect && completeFirstCorrect;
}

// Run the test
const testPassed = testCompletionSorting();
console.log(`\nOverall test result: ${testPassed ? 'PASSED' : 'FAILED'}`);

if (testPassed) {
    console.log('\n✅ Completion sorting functionality is working correctly!');
    console.log('The new sorting options should work properly in the application.');
} else {
    console.log('\n❌ There are issues with the completion sorting logic.');
}
