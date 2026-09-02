# ⚡ ReAct Agent for Cheshire Cat AI

[![awesome plugin](https://custom-icon-badges.demolab.com/static/v1?label=&message=awesome+plugin&color=383938&style=for-the-badge&logo=cheshire_cat_ai)](https://) [![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/Pingdred/ccat_af_react)

**ReAct Agent** is a specialized agent plugin for Cheshire Cat AI that implements the ReAct (Reasoning and Acting) methodology. This agent combines reasoning capabilities with action execution, allowing the Cat to think through problems step-by-step while using available tools to solve complex tasks.

## 🎯 What is ReAct?

ReAct (Reasoning and Acting) is a paradigm that interleaves reasoning traces and task-specific actions, enabling the agent to:
- **Reason** about the current situation and plan the next steps
- **Act** by executing tools and procedures
- **Observe** the results and adjust the approach accordingly

## ✨ Key Features

- **🧠 Step-by-Step Reasoning**: Agent thinks through problems methodically before acting
- **🔄 Iterative Problem Solving**: Continuously refines approach based on results
- **⚡ Tool Integration**: Seamlessly executes available procedures and tools
- **📝 Memory Integration**: Accesses both episodic and declarative memory
- **🎛️ Configurable Limits**: Adjustable iteration and procedure call limits
- **💬 Real-time Feedback**: Sends intermediate results during processing

## 🚀 Quick Start

### Prerequisites
This plugin requires the **Agent Factory** plugin to be installed and active.

### Installation
1. Install the Agent Factory plugin first
2. Download and install the ReAct Agent plugin
3. Go to **Plugins** → **React Agent** in the admin panel
4. Configure the agent settings as needed
5. In **Agent Factory** settings, select "ReAct Agent" as your active agent

### Configuration
The plugin offers several configurable parameters:

- **System Prompt**: Customize the agent's behavior and personality
- **Max Iterations**: Set the maximum number of reasoning-action cycles (default: 5)
- **Max Procedures Calls**: Limit procedure calls per iteration (default: 10)