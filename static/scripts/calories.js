let totalCalories = 0;

function addCalories() {
    console.log("addCalories function is triggered");
    const foodItem = document.getElementById('food-item').value;
    const calories = parseInt(document.getElementById('calories').value);
    
    if (!foodItem || isNaN(calories)) {
        alert("Please enter a valid food item and calorie amount.");
        return;
    }
    
    totalCalories += calories;
    document.getElementById('total-calories').textContent = totalCalories;
    
    // Clear the input fields
    document.getElementById('food-item').value = '';
    document.getElementById('calories').value = '';
}