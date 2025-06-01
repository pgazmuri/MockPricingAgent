# Multi-Agent Healthcare System - Usage Guide

## Overview

This system demonstrates a sophisticated multi-agent architecture for healthcare/pharmacy services using OpenAI's Assistant API. The system features **clean handoff mechanisms** between specialized agents that can seamlessly transfer conversations based on user needs.

## 🏗️ Architecture

### **Coordinator Pattern**
- **Agent Coordinator**: Central orchestrator that routes requests and manages handoffs
- **Specialized Agents**: Domain experts that can hand off to each other when needed

### **Available Agents**
1. **🔐 Authentication Agent** - Member verification, login, security checks
2. **💰 Pricing Agent** - Drug costs, insurance calculations, mathematical operations
3. **🏥 Pharmacy Agent** - Prescription management, refills, transfers
4. **📋 Benefits Agent** - Plan coverage, formulary, prior authorizations
5. **⚕️ Clinical Agent** - Drug interactions, therapeutic alternatives, safety

## 🚀 How to Run

### **Method 1: Multi-Agent Application (Recommended)**
```bash
cd c:\Repos\MockPricingAgent
python multi_agent_app.py
```

### **Method 2: Original Single Assistant**
```bash
python main.py
```

## 📋 Key Use Cases to Explore

### **1. Authentication → Pricing Handoff**
**Scenario**: User needs to login first, then check drug costs
```
User: "I need to log in with member ID DEMO123456"
🔐 Auth Agent: [Handles verification]
User: "Now how much does Lisinopril cost?"
🔄 Handoff: Auth → Pricing
💰 Pricing Agent: [Provides cost calculation]
```

### **2. Pricing → Pharmacy Handoff**
**Scenario**: Cost inquiry leads to prescription management
```
User: "What's the cost of Metformin?"
💰 Pricing Agent: [Calculates costs]
User: "Can I get a refill for that?"
🔄 Handoff: Pricing → Pharmacy
🏥 Pharmacy Agent: [Processes refill request]
```

### **3. Benefits → Clinical Handoff**
**Scenario**: Coverage question leads to therapeutic alternatives
```
User: "Is Nexium covered by my plan?"
📋 Benefits Agent: [Checks coverage]
User: "What alternatives are available if not covered?"
🔄 Handoff: Benefits → Clinical
⚕️ Clinical Agent: [Recommends alternatives]
```

### **4. Clinical → Pricing Handoff**
**Scenario**: Drug safety check leads to cost comparison
```
User: "Check interactions between Lisinopril and Metformin"
⚕️ Clinical Agent: [Analyzes interactions]
User: "How much would alternative drugs cost?"
🔄 Handoff: Clinical → Pricing
💰 Pricing Agent: [Compares costs]
```

### **5. Complex Multi-Agent Workflow**
**Scenario**: Complete medication management workflow
```
1. 🔐 Login/Authentication
2. 🏥 Check prescription status
3. 💰 Calculate refill costs
4. 📋 Verify plan coverage
5. ⚕️ Check for interactions
6. 🏥 Process refill request
```

## 🎯 Demo Scenarios

The application includes built-in demo scenarios:

### **Demo Mode**
- **Guided scenarios** showing automatic handoffs
- **Step-by-step explanations** of agent decisions
- **Visual indicators** of conversation flow

### **Interactive Mode**
- **Natural conversation** with intelligent routing
- **Real-time handoffs** based on context
- **State tracking** showing current agent and context

## 💡 Testing the Handoff Mechanisms

### **What to Look For:**

1. **Automatic Routing**
   - Coordinator determines the right initial agent
   - Agents recognize when they can't handle a request

2. **Clean Handoffs**
   - Smooth transitions between agents
   - Context preservation across handoffs
   - Clear explanations of why handoffs occur

3. **Intelligent Decision Making**
   - Agents use context to make handoff decisions
   - Multiple agents can be involved in complex workflows
   - Return to coordinator when tasks complete

## 🔧 Key Features to Test

### **1. NDC Drug Lookup**
```
"Look up Lisinopril 10mg tablets"
"Find generic versions of Nexium"
```

### **2. Mathematical Pricing Calculations**
```
"Calculate my copay if the drug costs $150 and my coinsurance is 20%"
"What's my out-of-pocket if I've met 60% of my deductible?"
```

### **3. Member Data Integration**
```
"Check eligibility for member DEMO123456"
"What's my plan utilization so far this year?"
```

### **4. Prescription Management**
```
"Check status of all my prescriptions"
"Transfer prescription RX123456 to a different pharmacy"
"Find pharmacies near ZIP code 12345"
```

### **5. Clinical Safety Checks**
```
"Check interactions between [drug1] and [drug2]"
"Find therapeutic alternatives for Lipitor"
"Check if I'm allergic to penicillin"
```

## 🎭 Advanced Use Cases

### **1. Step Therapy Workflow**
```
User: "I need Humira for my arthritis"
📋 Benefits: "This requires step therapy - trying methotrexate first"
⚕️ Clinical: "Here are the step therapy requirements and timeline"
💰 Pricing: "Here's the cost comparison between options"
```

### **2. Prior Authorization Process**
```
User: "My doctor prescribed Xeljanz"
📋 Benefits: "This requires prior authorization"
⚕️ Clinical: "Here are the clinical criteria needed"
🏥 Pharmacy: "I can help submit the PA request"
```

### **3. Emergency Drug Interaction**
```
User: "I was just prescribed warfarin, I take aspirin daily"
⚕️ Clinical: "MAJOR INTERACTION ALERT - bleeding risk!"
🏥 Pharmacy: "Contact your prescriber immediately"
💰 Pricing: "Here are safer alternative costs"
```

## 🔍 Monitoring Agent Behavior

### **Console Output Shows:**
- **Agent selection logic** - Why each agent was chosen
- **Function calls** - What data each agent retrieves
- **Handoff decisions** - When and why agents transfer
- **Context preservation** - How information flows between agents

### **Rich UI Features:**
- **Color-coded agents** - Easy visual identification
- **Real-time status** - Current agent and conversation state
- **Interactive commands** - Help, status, demo modes

## 🛠️ Customization Options

### **Adding New Agents:**
1. Extend `BaseAgent` class
2. Implement `process_message()` method
3. Add handoff capabilities with `request_handoff` function
4. Register with coordinator

### **Modifying Handoff Logic:**
- Update agent instructions for different handoff triggers
- Agents make intelligent handoff decisions based on their expertise
- Customize context sharing between agents

### **Performance Optimization:**
- Model selection (`gpt-4.1-mini` vs `gpt-4-1106-preview`)
- Polling intervals (currently 0.5s)
- Function call batching

## 🎯 Success Metrics

**Effective handoffs should demonstrate:**
- ✅ **Seamless transitions** - No conversation breaks
- ✅ **Context preservation** - Information carries over
- ✅ **Intelligent routing** - Right agent for each task
- ✅ **User satisfaction** - Natural conversation flow
- ✅ **Functional accuracy** - Correct data and calculations

This system showcases advanced patterns for multi-agent AI applications with real-world healthcare/pharmacy use cases!
