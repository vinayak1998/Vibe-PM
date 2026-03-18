"""Manual test script to simulate the full app flow with comprehensive answers."""

import asyncio
import sys
from pathlib import Path

# Add project root
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from orchestrator import Orchestrator


async def test_full_flow():
    """Test the complete flow from Discovery through Scoping to Spec Writing."""
    
    print("="*80)
    print("TESTING AI PM CHATBOT - FULL FLOW")
    print("="*80)
    print()
    
    orchestrator = Orchestrator()
    
    # Phase 1: Discovery
    print("\n" + "="*80)
    print("PHASE 1: DISCOVERY")
    print("="*80)
    
    # We'll use a more interactive approach - respond to what the agent asks
    # Keep comprehensive info ready to paste when asked
    comprehensive_info = {
        "idea": "DogMeet - a social app for urban dog owners to find dog-friendly parks, schedule playdates, and track their dog's health.",
        
        "target_user": "Urban millennials aged 25-40 who own dogs and live in apartments. They work full-time (often hybrid/remote) and are tech-savvy, already using apps like Rover and BarkBox.",
        
        "typical_day": "Sarah, 32, works from home in Seattle with her golden retriever Max. At lunch she spends 30+ minutes searching Google Maps and Yelp for dog parks, checks Facebook groups to coordinate playdates (lots of back-and-forth), then manually logs Max's exercise in a spreadsheet. She visits the park 4-5 days per week. If she can't find a good spot, she just walks Max around the block instead, which isn't enough exercise.",
        
        "core_problem": "Dog owners in cities spend 30+ minutes daily searching for dog-friendly parks (Google Maps has no dog-specific filters), have no easy way to coordinate playdates (Facebook groups are clunky), and rely on paper or spreadsheets to track health. This leads to lonely, under-exercised dogs and stressed owners.",
        
        "alternatives": "Google Maps for finding parks (no dog-specific features), Facebook groups for playdates (hard to coordinate), spreadsheets or paper for health tracking, BarkHappy app (US-only and poorly maintained).",
        
        "why_now": "Post-pandemic dog ownership surged 30%. Remote/hybrid work means flexible schedules for midday park visits. GPS and health wearables for dogs like FitBark are now mainstream, creating integration opportunities.",
        
        "features": "Park finder with dog-specific ratings and reviews, playdate scheduling with in-app chat, dog health and exercise tracker with vet visit reminders, dog profile with breed/age/temperament for matching, and a social feed for sharing dog photos.",
        
        "success_metrics": "Monthly active users, playdates scheduled per week, and user retention at 30/60/90 days. Target: 10K MAU in first 6 months, 5 playdates per user per month, 60% retention at 90 days.",
        
        "revenue": "Freemium model. Free: park finder and basic tracking. Premium ($5/month): unlimited playdates, advanced health analytics, and vet telehealth. Also local business ads from pet stores and groomers.",
        
        "constraints": "3-month timeline to MVP, 2-person team (1 developer and 1 designer), $10K budget. Must launch on iOS first, Android later. Need to comply with pet data privacy regulations.",
        
        "milestone": "MVP with park finder and playdate scheduling in 3 months."
    }
    
    # Start with initial idea
    discovery_answers = [comprehensive_info["idea"]]
    
    conversation_log = []
    
    # Predefined responses for common question patterns
    def get_response_for_question(question: str) -> str:
        """Match agent question to appropriate comprehensive answer."""
        q_lower = question.lower()
        
        if any(word in q_lower for word in ["target", "user", "persona", "ideal", "customer", "typical day", "who"]):
            return comprehensive_info["typical_day"]
        elif any(word in q_lower for word in ["problem", "pain", "struggle", "challenge"]):
            return comprehensive_info["core_problem"]
        elif any(word in q_lower for word in ["alternative", "currently", "existing", "competition"]):
            return comprehensive_info["alternatives"]
        elif any(word in q_lower for word in ["why now", "timing", "moment"]):
            return comprehensive_info["why_now"]
        elif any(word in q_lower for word in ["feature", "functionality", "capability", "wishlist"]):
            return comprehensive_info["features"]
        elif any(word in q_lower for word in ["metric", "measure", "success", "kpi"]):
            return comprehensive_info["success_metrics"]
        elif any(word in q_lower for word in ["revenue", "monetize", "money", "pricing", "business model"]):
            return comprehensive_info["revenue"]
        elif any(word in q_lower for word in ["constraint", "limit", "timeline", "budget", "team"]):
            return comprehensive_info["constraints"]
        elif any(word in q_lower for word in ["milestone", "mvp", "first"]):
            return comprehensive_info["milestone"]
        else:
            # Provide a comprehensive answer that covers multiple areas
            return f"{comprehensive_info['target_user']} {comprehensive_info['core_problem']} {comprehensive_info['alternatives']}"
    
    max_discovery_turns = 15
    
    for i in range(max_discovery_turns):
        if i == 0:
            user_msg = discovery_answers[0]
        else:
            # Get response based on last agent question
            if orchestrator.state.phase != "discovery":
                break
            
            last_response = conversation_log[-1]["assistant"] if conversation_log else ""
            user_msg = get_response_for_question(last_response)
        
        print(f"\n--- Discovery Turn {i+1} ---")
        print(f"USER: {user_msg[:300]}{'...' if len(user_msg) > 300 else ''}")
        print()
        
        try:
            response, state = await orchestrator.handle_message(user_msg)
            print(f"AGENT ({state.phase}): {response[:500]}{'...' if len(response) > 500 else ''}")
            conversation_log.append({
                "user": user_msg,
                "assistant": response,
                "phase": state.phase
            })
            
            # Check if agent is showing summary or asking for confirmation
            if "does that sound right" in response.lower() or "is this accurate" in response.lower() or "confirm" in response.lower():
                print("\n[Agent appears to be asking for confirmation of summary]")
                # Confirm and move to next phase
                confirm_msg = "Yes, that's perfect! Let's move forward with scoping."
                print(f"\n--- Confirmation Turn ---")
                print(f"USER: {confirm_msg}")
                print()
                
                response, state = await orchestrator.handle_message(confirm_msg)
                print(f"AGENT ({state.phase}): {response}")
                conversation_log.append({
                    "user": confirm_msg,
                    "assistant": response,
                    "phase": state.phase
                })
            
            # Check if we've moved to scoping
            if state.phase == "scoping":
                print("\n✓ Transitioned to SCOPING phase")
                break
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
    
    # Phase 2: Scoping
    print("\n" + "="*80)
    print("PHASE 2: SCOPING")
    print("="*80)
    
    # Wait for scoping to complete (it does web research)
    print("\nWaiting for scoping agent to do web research and propose RICE-scored features...")
    
    max_scoping_turns = 5
    scoping_responses = [
        "I agree with prioritizing the park finder and playdate scheduling for MVP. Health tracking can come in phase 2.",
        "Yes, that sounds reasonable. Let's go with that scope.",
        "Looks good to me. The social feed can wait for v2.",
        "Perfect, I'm happy with this plan.",
        "Yes, let's proceed with this scope."
    ]
    
    for i in range(max_scoping_turns):
        if orchestrator.state.phase != "scoping":
            break
            
        user_msg = scoping_responses[i % len(scoping_responses)]
        print(f"\n--- Scoping Turn {i+1} ---")
        print(f"USER: {user_msg}")
        print()
        
        try:
            response, state = await orchestrator.handle_message(user_msg)
            print(f"AGENT ({state.phase}): {response}")
            conversation_log.append({
                "user": user_msg,
                "assistant": response,
                "phase": state.phase
            })
            
            if state.phase == "spec":
                print("\n✓ Transitioned to SPEC WRITING phase")
                break
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
    
    # Phase 3: Spec Writing
    print("\n" + "="*80)
    print("PHASE 3: SPEC WRITING")
    print("="*80)
    
    print("\nWaiting for spec writer to generate the final product spec...")
    
    # Spec writer should automatically generate and move to "done"
    # If it asks questions, respond
    max_spec_turns = 3
    spec_responses = [
        "Yes, please generate the spec.",
        "That looks great, thank you!",
        "Perfect!"
    ]
    
    for i in range(max_spec_turns):
        if orchestrator.state.phase == "done":
            print("\n✓ Reached DONE phase - spec generated successfully!")
            break
            
        if orchestrator.state.phase != "spec":
            break
            
        user_msg = spec_responses[i % len(spec_responses)]
        print(f"\n--- Spec Turn {i+1} ---")
        print(f"USER: {user_msg}")
        print()
        
        try:
            response, state = await orchestrator.handle_message(user_msg)
            print(f"AGENT ({state.phase}): {response}")
            conversation_log.append({
                "user": user_msg,
                "assistant": response,
                "phase": state.phase
            })
            
            if state.phase == "done":
                print("\n✓ Reached DONE phase - spec generated successfully!")
                break
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
    
    # Final Results
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    print()
    print(f"Total turns: {len(conversation_log)}")
    print(f"Final phase: {orchestrator.state.phase}")
    print(f"Phases visited: {[t['phase'] for t in conversation_log]}")
    print()
    
    if orchestrator.state.spec_markdown:
        print(f"✓ Spec generated successfully!")
        print(f"  Spec length: {len(orchestrator.state.spec_markdown)} characters")
        print()
        print("First 500 characters of spec:")
        print("-" * 80)
        print(orchestrator.state.spec_markdown[:500])
        print("-" * 80)
        
        # Save spec to file
        spec_path = Path(__file__).parent / "test_output_spec.md"
        spec_path.write_text(orchestrator.state.spec_markdown)
        print()
        print(f"✓ Full spec saved to: {spec_path}")
    else:
        print("✗ No spec generated")
    
    print()
    print("="*80)
    print("TEST COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_full_flow())
