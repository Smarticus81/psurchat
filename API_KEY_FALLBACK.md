# ✅ API Key Fallback System - Flexible Provider Support

## 🎯 Overview

The Multi-Agent PSUR System now supports **intelligent API key fallback**, meaning you can run the system with **just 1-2 API keys** instead of requiring all 4!

---

## 💡 How It Works

### **Minimum Requirement: 1 API Key**
You only need **ONE** of the following:
- `OPENAI_API_KEY` (recommended - powers 8 agents)
- `ANTHROPIC_API_KEY` (recommended - powers 5 agents)
- `GOOGLE_API_KEY` (powers 4 agents)
- `PERPLEXITY_API_KEY` (powers 1 agent)

### **Automatic Fallback**
If an agent's preferred provider is unavailable, it automatically uses whichever provider you have configured.

**Fallback Priority:**
```
Preferred Provider Not Available?
    ↓
Try OpenAI
    ↓
Try Anthropic
    ↓
Try Google
    ↓
Try Perplexity
    ↓
Error (no providers available)
```

---

## 📊 Agent Provider Preferences

### **Originally Assigned:**
- **OpenAI (8 agents):** Diana, Vera, Frank, Brianna, Victoria, Quincy, Statler, Charley
- **Anthropic (5 agents):** Alex, Raj, Tara, Rita, Marcus
- **Google (4 agents):** Sam, Carla, Cameron, Clara
- **Perplexity (1 agent):** Eddie

### **With Fallback:**
All 19 agents will work with **any single provider** you have configured!

---

## 🔧 Configuration Examples

### **Example 1: OpenAI Only**
```env
OPENAI_API_KEY=sk-your-key-here
# ANTHROPIC_API_KEY=  (not set)
# GOOGLE_API_KEY=     (not set)
# PERPLEXITY_API_KEY= (not set)
```

**Result:**
- All 19 agents use OpenAI
- System prints warnings showing fallbacks:
  ```
  ⚠️  Alex (Orchestrator): anthropic → openai
  ⚠️  Sam (Scope): google → openai
  ✅ Diana (Device ID): openai
  ```

### **Example 2: OpenAI + Anthropic (Recommended)**
```env
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
# GOOGLE_API_KEY=     (not set)
# PERPLEXITY_API_KEY= (not set)
```

**Result:**
- OpenAI agents: Use OpenAI ✅
- Anthropic agents: Use Anthropic ✅
- Google agents: Fallback to OpenAI ⚠️
- Perplexity agents: Fallback to OpenAI ⚠️

### **Example 3: All Providers (Optimal)**
```env
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=your-google-key
PERPLEXITY_API_KEY=pplx-your-key
```

**Result:**
- Every agent uses its preferred provider ✅
- No fallbacks needed
- Optimal performance and cost distribution

---

## 📋 Setup Instructions

### **Step 1: Copy .env.example to .env**
```bash
cd backend
cp .env.example .env
```

### **Step 2: Add At Least ONE API Key**
Edit `.env` and add your API key(s):

```env
# Minimum - add just one:
OPENAI_API_KEY=sk-proj-...

# Recommended - add two:
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

### **Step 3: Initialize Database**
```bash
python quickstart.py
```

**You'll see provider status:**
```
============================================================
AI Provider Status:
============================================================
✅ OpenAI      - Available (gpt-5.2)
✅ Anthropic   - Available (claude-sonnet-4)
⚠️  Google     - Not configured (will fallback)
⚠️  Perplexity - Not configured (will fallback)
============================================================

✅ 2 provider(s) available - System ready!
============================================================
```

### **Step 4: Start Backend**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

---

## 🎨 Visual Feedback

### **During Database Initialization:**
The system shows which agents are using fallbacks:

```
Seeding agents for session 1...
  ✅ Alex (Orchestrator): anthropic
  ✅ Diana (Device Identification): openai
  ⚠️  Sam (Scope & Documentation): google → openai
  ✅ Raj (Sales Analysis): anthropic
  ✅ Vera (Vigilance Monitor): openai
  ⚠️  Carla (Complaint Classifier): google → openai
  ...
```

**Legend:**
- ✅ = Using preferred provider
- ⚠️ = Using fallback provider

---

## 💰 Cost Optimization

### **Strategy 1: OpenAI Only (Simple & Cost-Effective)**
- **Cost:** Pay-per-use, predictable pricing
- **Quality:** Excellent for all tasks
- **Setup:** Easiest (1 API key)

### **Strategy 2: OpenAI + Anthropic (Recommended)**
- **Cost:** Distribute load across providers
- **Quality:** Best of both worlds (GPT for precision, Claude for reasoning)
- **Setup:** Easy (2 API keys)

### **Strategy 3: All Providers (Optimal Performance)**
- **Cost:** Higher variety, can use free tiers
- **Quality:** Each agent uses its ideal model
- **Setup:** More complex (4 API keys)

---

## 🔍 Technical Details

### **How Fallback Works:**

1. **Agent Configuration** (`config.py`):
   ```python
   AgentConfig(
       name="Sam",
       ai_provider="google",  # Preferred
       model="gemini-2.0-flash-exp"
   )
   ```

2. **Fallback Check** (at runtime):
   ```python
   def get_active_provider(self):
       # Check if Google API key exists
       if settings.google_api_key:
           return "google", "gemini-2.0-flash-exp"
       # Fallback to OpenAI
       if settings.openai_api_key:
           return "openai", "gpt-5.2"
       # Continue fallback chain...
   ```

3. **Database Seeding**:
   - Agents are created with **actual** provider (post-fallback)
   - Frontend shows the provider being used
   - No runtime surprises

---

## ⚠️ Important Notes

### **API Key Requirements:**
- At least **ONE** API key must be set
- System will error on startup if **zero** keys configured
- Recommendation: Set `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` minimum

### **Model Compatibility:**
- Fallback models may differ from preferred
- Quality remains high (all are frontier models)
- No functionality is lost

### **Provider Preferences Matter:**
- Orchestrator (Alex) works best with Claude
- QC Validator (Victoria) works best with GPT
- But both will work fine with fallbacks

---

## 🧪 Testing Fallback

### **Test 1: OpenAI Only**
```bash
# .env
OPENAI_API_KEY=sk-...
# Others commented out

# Run
python quickstart.py
```

**Expected Output:**
```
✅ OpenAI - Available
⚠️  Anthropic - Not configured
⚠️  Google - Not configured
⚠️  Perplexity - Not configured

✅ 1 provider(s) available - System ready!
```

### **Test 2: No API Keys**
```bash
# .env
# All commented out

# Run
python quickstart.py
```

**Expected Output:**
```
❌ ERROR: No AI providers configured!
   Please add at least OPENAI_API_KEY or ANTHROPIC_API_KEY to .env
```

---

## ✅ Summary

**Benefits:**
- ✅ Run with just 1 API key (vs. requiring 4)
- ✅ Automatic intelligent fallback
- ✅ Clear visual feedback on what's happening
- ✅ No functionality lost
- ✅ Cost optimization possible

**Recommended Setup:**
```env
OPENAI_API_KEY=sk-proj-...      # For 8 agents
ANTHROPIC_API_KEY=sk-ant-...    # For 5 agents
# Google & Perplexity optional
```

---

## 🚀 Ready to Go!

With the fallback system, you can start using the Multi-Agent PSUR System with **minimal setup** and **maximum flexibility**!

Just add your OpenAI and/or Anthropic API key, run `python quickstart.py`, and you're ready! 🎉
