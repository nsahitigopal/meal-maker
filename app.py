from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import json
import re
from openai import OpenAI
import os

load_dotenv()


api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def calculate_tdee(gender, age, weight, height_ft, activity_level, focus):
    # Convert height to cm
    height_cm = height_ft * 30.48
    
    # Calculate BMR using Mifflin-St Jeor Equation
    if gender.lower() == "male":
        bmr = 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
    else:
        bmr = 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)
    
    # Activity multipliers
    multipliers = {
        "Sedentary": 1.2, "Light": 1.375, "Moderate": 1.55, "Active": 1.725
    }
    
    # Calculate base TDEE and adjust for goal
    base_tdee = bmr * multipliers.get(activity_level, 1.2)
    
    # Goal-based adjustments
    adjustments = {
        "Weight Loss": 0.8, "Weight Gain": 1.1, 
        "Muscle Building": 1.15, "Maintenance": 1.0
    }
    
    return round(base_tdee * adjustments.get(focus, 1.0), 0)

def calculate_macros(tdee, weight, focus):
    # Define protein ratios based on goals
    protein_ratios = {
        "Weight Loss": 2.2, "Muscle Building": 2.2,
        "Weight Gain": 1.8, "Maintenance": 1.6
    }
    
    # Define fat percentages based on goals
    fat_percentages = {
        "Weight Loss": 0.25, "Muscle Building": 0.25,
        "Weight Gain": 0.25, "Maintenance": 0.3
    }
    
    # Calculate macros
    protein_g = weight * protein_ratios.get(focus, 1.6)
    fat_g = (tdee * fat_percentages.get(focus, 0.3)) / 9
    carbs_g = (tdee - (protein_g * 4) - (fat_g * 9)) / 4
    fiber_g = (tdee / 1000) * 14
    
    # Ensure non-negative values and round
    return {
        "protein": max(0, round(protein_g, 1)),
        "carbs": max(0, round(carbs_g, 1)),
        "fat": max(0, round(fat_g, 1)),
        "fiber": round(fiber_g, 1)
    }

def generate_meal_plan(tdee, eating_habit, allergies, health_issues, focus, weight, macros, day=None, meal_type=None):
    # Prepare context strings
    allergies_text = f"Avoid these allergens: {allergies}." if allergies else "No specific allergies."
    health_text = f"Consider health conditions: {health_issues}." if health_issues else "No specific health conditions."
    
    # Define goal-specific guidance
    focus_guidance = {
        "Weight Loss": "Higher protein, moderate fat, lower carbs. Emphasize fiber and vegetables for satiety.",
        "Weight Gain": "Higher carbs and calories, moderate protein and fat. Include calorie-dense foods.",
        "Muscle Building": f"High protein ({macros['protein']}g daily), moderate carbs and fat. Space protein intake evenly.",
        "Maintenance": "Balanced macronutrients. Focus on whole foods."
    }
    
    # Meal distribution percentages
    meal_distribution = {
        "Weight Loss": {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.3, "snacks": 0.1},
        "Weight Gain": {"breakfast": 0.25, "lunch": 0.3, "dinner": 0.3, "snacks": 0.15},
        "Muscle Building": {"breakfast": 0.25, "lunch": 0.3, "dinner": 0.3, "snacks": 0.15},
        "Maintenance": {"breakfast": 0.25, "lunch": 0.3, "dinner": 0.3, "snacks": 0.15}
    }
    
    current_distribution = meal_distribution.get(focus, meal_distribution["Maintenance"])
    
    # Build prompt based on request type
    if day and meal_type:
        meal_calories = round(tdee * current_distribution[meal_type.lower()])
        meal_protein = round(macros['protein'] * current_distribution[meal_type.lower()])
        
        prompt = f"""
        Generate a South Indian {eating_habit.lower()} meal for {meal_type} on Day {day}.
        
        Profile: Focus: {focus}, Calories: {tdee} kcal, {allergies_text} {health_text}
        
        Requirements:
        - Approximately {meal_calories} kcal with ~{meal_protein}g protein
        - South Indian cuisine for {eating_habit.lower()} diet
        - {focus_guidance.get(focus, "")}
        
        Return ONLY valid JSON in this format (no explanation, markdown, or code blocks):
        {{
          "meal": {{
            "name": "Meal Name",
            "ingredients": ["ingredient1", "ingredient2", "..."],
            "calories": {meal_calories},
            "protein": {meal_protein},
            "carbs": 0,
            "fat": 0,
            "fiber": 0,
            "preparation": "Brief preparation instructions"
          }}
        }}
        """
    else:
        # Format macro guidance
        macro_guidance = f"""Protein: {macros['protein']}g, Carbs: {macros['carbs']}g, Fat: {macros['fat']}g, Fiber: {macros['fiber']}g minimum"""
        
        prompt = f"""
        Generate a 7-day South Indian {eating_habit.lower()} meal plan.
        
        Profile: Focus: {focus}, Calories: {tdee} kcal, {allergies_text} {health_text}
        
        Requirements:
        - {focus_guidance.get(focus, "")}
        - Daily targets: {macro_guidance}
        - Each day must add up to {tdee} kcal (±10 kcal)
        - Traditional South Indian cuisine adapted to meet macro goals
        
        Return ONLY valid JSON in this exact format (no explanation, markdown, or code blocks):
        {{
          "meal_plan": [
            {{
              "day": 1,
              "breakfast": {{ 
                "name": "Meal Name",
                "ingredients": ["ingredient1", "ingredient2"],
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "fiber": 0,
                "preparation": "Brief preparation instructions"
              }},
              "lunch": {{ 
                "name": "Meal Name",
                "ingredients": ["ingredient1", "ingredient2"],
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "fiber": 0,
                "preparation": "Brief preparation instructions"
              }},
              "dinner": {{ 
                "name": "Meal Name",
                "ingredients": ["ingredient1", "ingredient2"],
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "fiber": 0,
                "preparation": "Brief preparation instructions"
              }},
              "snacks": {{ 
                "name": "Meal Name",
                "ingredients": ["ingredient1", "ingredient2"],
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "fiber": 0,
                "preparation": "Brief preparation instructions"
              }}
            }},
            {{
              "day": 2,
              "breakfast": {{ ... }},
              "lunch": {{ ... }},
              "dinner": {{ ... }},
              "snacks": {{ ... }}
            }},
            ... and so on for 7 days
          ]
        }}
        """
    
    # Call OpenAI API
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are an expert dietitian specializing in South Indian cuisine. Return ONLY valid parseable JSON with no explanation, markdown formatting, or code blocks."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}  # Force JSON response format
    )
    
    # Process response
    try:
        raw_response = completion.choices[0].message.content.strip()
        
        # Clean up any potential formatting issues
        # Remove any markdown code blocks
        raw_response = re.sub(r'```json\s*', '', raw_response)
        raw_response = re.sub(r'```\s*', '', raw_response)
        
        # Parse the JSON response
        response = json.loads(raw_response)
        
        # Return specific meal or full plan
        if day and meal_type:
            return response.get("meal", None)
        
        # Validate and process meal plan
        meal_plan = response.get("meal_plan", [])
        for day_plan in meal_plan:
            day_num = day_plan.get("day", "unknown")
            
            # Calculate daily totals
            day_calories = 0
            day_protein = 0
            day_carbs = 0
            day_fat = 0
            day_fiber = 0
            
            for meal in ["breakfast", "lunch", "dinner", "snacks"]:
                meal_data = day_plan.get(meal, {})
                day_calories += meal_data.get("calories", 0)
                day_protein += meal_data.get("protein", 0)
                day_carbs += meal_data.get("carbs", 0)
                day_fat += meal_data.get("fat", 0)
                day_fiber += meal_data.get("fiber", 0)
            
            # Add totals to the day plan
            day_plan["total_calories"] = day_calories
            day_plan["total_protein"] = day_protein
            day_plan["total_carbs"] = day_carbs
            day_plan["total_fat"] = day_fat
            day_plan["total_fiber"] = day_fiber
            
            # Verify calories are within tolerance
            if abs(day_calories - tdee) > 50:
                st.warning(f"Day {day_num} calories ({day_calories}) differ from target ({tdee}) by more than 50 kcal")
        
        return meal_plan
        
    except json.JSONDecodeError as e:
        st.error(f"Error: Invalid JSON received. Please try again. Error details: {str(e)}")
        return None

def create_meal_day_table(day_data, macros_target):
    """Create a DataFrame for a specific day's meal plan"""
    meals = ["breakfast", "lunch", "dinner", "snacks"]
    meal_data = []
    
    # Add each meal to data
    for meal_type in meals:
        meal = day_data.get(meal_type, {})
        if meal:
            meal_data.append({
                "Meal": meal_type.capitalize(),
                "Name": meal.get("name", ""),
                "Calories": meal.get("calories", 0),
                "Protein (g)": meal.get("protein", 0),
                "Carbs (g)": meal.get("carbs", 0), 
                "Fat (g)": meal.get("fat", 0),
                "Fiber (g)": meal.get("fiber", 0),
                "Ingredients": ", ".join(meal.get("ingredients", [])),
                "Preparation": meal.get("preparation", "")
            })
    
    # Calculate totals
    total_calories = sum(meal.get("Calories", 0) for meal in meal_data)
    total_protein = sum(meal.get("Protein (g)", 0) for meal in meal_data)
    total_carbs = sum(meal.get("Carbs (g)", 0) for meal in meal_data)
    total_fat = sum(meal.get("Fat (g)", 0) for meal in meal_data)
    total_fiber = sum(meal.get("Fiber (g)", 0) for meal in meal_data)
    
    # Add totals row with percentages
    meal_data.append({
        "Meal": "**DAILY TOTAL**",
        "Name": "",
        "Calories": total_calories,
        "Protein (g)": f"{total_protein} ({round((total_protein/macros_target['protein'])*100)}%)",
        "Carbs (g)": f"{total_carbs} ({round((total_carbs/macros_target['carbs'])*100)}%)", 
        "Fat (g)": f"{total_fat} ({round((total_fat/macros_target['fat'])*100)}%)",
        "Fiber (g)": f"{total_fiber} ({round((total_fiber/macros_target['fiber'])*100)}%)",
        "Ingredients": "",
        "Preparation": ""
    })
    
    return pd.DataFrame(meal_data)

# Streamlit UI
st.title("South Indian Meal Plan Generator")

# Two-column layout for inputs
col1, col2 = st.columns(2)

with col1:
    st.subheader("Personal Details")
    gender = st.selectbox("Gender", ["Male", "Female"])
    age = st.number_input("Age", min_value=10, max_value=100, value=30)
    weight = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=60.0)
    height_ft = st.number_input("Height (ft)", min_value=4.0, max_value=7.0, value=5.6)

with col2:
    st.subheader("Dietary Preferences")
    activity_level = st.selectbox("Activity Level", ["Sedentary", "Light", "Moderate", "Active"])
    focus = st.selectbox("Goal", ["Maintenance", "Weight Loss", "Weight Gain", "Muscle Building"])
    eating_habit = st.selectbox("Diet Type", ["Vegetarian", "Non-Vegetarian", "Eggetarian"])
    allergies = st.text_input("Allergies", "")
    health_issues = st.text_input("Health Conditions", "")

# Initialize session state
for key in ["tdee", "macros", "meal_plan"]:
    if key not in st.session_state:
        st.session_state[key] = None

# Generate button
if st.button("Generate Meal Plan"):
    with st.spinner("Creating your personalized meal plan..."):
        st.session_state["tdee"] = calculate_tdee(gender, age, weight, height_ft, activity_level, focus)
        st.session_state["macros"] = calculate_macros(st.session_state["tdee"], weight, focus)
        
        # Show calculations even if the meal plan generation fails
        if st.session_state["tdee"] and st.session_state["macros"]:
            st.subheader("Your Nutrition Profile")
            
            # Create compact summary table
            summary_data = {
                "Metric": ["Calories", "Protein", "Carbs", "Fat", "Fiber"],
                "Value": [
                    f"{int(st.session_state['tdee'])} kcal",
                    f"{st.session_state['macros']['protein']}g ({round(st.session_state['macros']['protein'] * 4 / st.session_state['tdee'] * 100)}%)",
                    f"{st.session_state['macros']['carbs']}g ({round(st.session_state['macros']['carbs'] * 4 / st.session_state['tdee'] * 100)}%)",
                    f"{st.session_state['macros']['fat']}g ({round(st.session_state['macros']['fat'] * 9 / st.session_state['tdee'] * 100)}%)",
                    f"{st.session_state['macros']['fiber']}g min"
                ]
            }
            st.table(pd.DataFrame(summary_data))
        
        # Generate meal plan
        st.session_state["meal_plan"] = generate_meal_plan(
            st.session_state["tdee"], eating_habit, allergies.strip(), 
            health_issues.strip(), focus, weight, st.session_state["macros"]
        )

# Display meal plan with tabs
if st.session_state["meal_plan"]:
    st.subheader("7-Day South Indian Meal Plan")
    
    tab_days = st.tabs([f"Day {i+1}" for i in range(7)])
    
    for i, day in enumerate(st.session_state["meal_plan"]):
        with tab_days[i]:
            day_df = create_meal_day_table(day, st.session_state["macros"])
            
            # Compact/detailed view toggle
            view_mode = st.radio(f"View mode", ["Compact", "Detailed"], key=f"view_{day['day']}", horizontal=True)
            
            if view_mode == "Compact":
                st.dataframe(day_df[["Meal", "Name", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)"]], 
                             use_container_width=True)
            else:
                st.dataframe(day_df, use_container_width=True)
            
            # Regenerate meal buttons
            st.markdown("#### Regenerate Meals")
            cols = st.columns(4)
            
            for j, meal in enumerate(["breakfast", "lunch", "dinner", "snacks"]):
                with cols[j]:
                    if st.button(f"🔄 {meal.capitalize()}", key=f"{day['day']}_{meal}"):
                        with st.spinner(f"Regenerating {meal}..."):
                            new_meal = generate_meal_plan(
                                st.session_state["tdee"], eating_habit, allergies, health_issues, 
                                focus, weight, st.session_state["macros"], day["day"], meal
                            )
                            if new_meal:
                                day[meal] = new_meal
                                st.rerun()