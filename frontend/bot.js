// bot.js
const { Client, GatewayIntentBits, REST, Routes, EmbedBuilder } = require('discord.js');
const axios = require('axios');
require('dotenv').config();

// Configuration
const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const CLIENT_ID = process.env.CLIENT_ID;
const RAG_BACKEND_URL = process.env.RAG_BACKEND_URL || 'http://127.0.0.1:8000';

// Store conversation context for follow-ups
// Format: { userId: { lastQuery: string, lastAnswer: string, contexts: array } }
const conversationHistory = new Map();

// Create Discord client
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMessageReactions
    ]
});

// Query the RAG backend
async function queryRagBackend(query, k = 4, provider = 'azure') {
    try {
        const response = await axios.post(
            `${RAG_BACKEND_URL}/rag/answer`,
            { query, k, provider },
            { timeout: 30000 }
        );
        return response.data;
    } catch (error) {
        if (error.code === 'ECONNABORTED') {
            return { error: 'Request timed out. Please try again.' };
        } else if (error.response) {
            return { error: `Backend returned status ${error.response.status}: ${error.response.data}` };
        } else if (error.request) {
            return { error: 'Could not connect to backend. Please check if the server is running.' };
        } else {
            return { error: `Unexpected error: ${error.message}` };
        }
    }
}

// Format the RAG response for Discord
function formatResponse(data) {
    if (data.error) {
        return `❌ Sorry, I encountered an error: ${data.error}`;
    }

    let answer = data.answer || "I don't know.";
    const contexts = data.contexts || [];

    // Add source information if available
    if (contexts.length > 0) {
        answer += '\n\n**Sources:**';
        contexts.slice(0, 3).forEach((ctx, index) => {
            const source = ctx.source || 'Unknown';
            const score = ctx.score || 0;
            // Extract filename from path
            const filename = source.includes('/') ? source.split('/').pop() : source;
            answer += `\n${index + 1}. ${filename} (relevance: ${score.toFixed(2)})`;
        });
    }

    return answer;
}

// Add feedback reactions
async function addFeedbackReactions(message) {
    try {
        await message.react('👍');
        await message.react('👎');
    } catch (error) {
        console.log('Could not add reactions:', error.message);
    }
}

// Define slash commands
const commands = [
    {
        name: 'ask',
        description: 'Ask the FAQ bot a question',
        options: [
            {
                name: 'question',
                type: 3, // STRING type
                description: 'Your question about the bootcamp or internship',
                required: true
            }
        ]
    },
    {
        name: 'followup',
        description: 'Ask a follow-up question to your previous query',
        options: [
            {
                name: 'question',
                type: 3, // STRING type
                description: 'Your follow-up question',
                required: true
            }
        ]
    },
    {
        name: 'clear',
        description: 'Clear your conversation history'
    }
];

// Register slash commands
async function registerCommands() {
    const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);
    
    try {
        console.log('🔄 Registering slash commands...');
        await rest.put(
            Routes.applicationCommands(CLIENT_ID),
            { body: commands }
        );
        console.log('✅ Successfully registered slash commands!');
    } catch (error) {
        console.error('❌ Error registering commands:', error);
    }
}

// Bot ready event
client.once('ready', () => {
    console.log(`✅ ${client.user.tag} is now online!`);
    console.log(`📡 Connected to ${client.guilds.cache.size} guild(s)`);
    registerCommands();
});

// Handle slash commands
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) return;

    const { commandName, user } = interaction;

    if (commandName === 'ask') {
        const question = interaction.options.getString('question');
        
        await interaction.deferReply();

        // Query the backend
        const result = await queryRagBackend(question);

        // Format and send response
        const responseText = formatResponse(result);
        const reply = await interaction.editReply(responseText);

        // Add feedback reactions
        await addFeedbackReactions(reply);

        // Store conversation context
        if (!result.error) {
            conversationHistory.set(user.id, {
                lastQuery: question,
                lastAnswer: result.answer || '',
                contexts: result.contexts || []
            });
        }
    }

    else if (commandName === 'followup') {
        const question = interaction.options.getString('question');

        if (!conversationHistory.has(user.id)) {
            await interaction.reply({
                content: "❌ You haven't asked me anything yet! Use `/ask` to start a conversation.",
                ephemeral: true
            });
            return;
        }

        await interaction.deferReply();

        // Build context-aware query
        const previous = conversationHistory.get(user.id);
        const contextualQuery = `Previous question: ${previous.lastQuery}\nFollow-up: ${question}`;

        // Query the backend
        const result = await queryRagBackend(contextualQuery);

        // Format and send response
        const responseText = formatResponse(result);
        const reply = await interaction.editReply(responseText);

        // Add feedback reactions
        await addFeedbackReactions(reply);

        // Update conversation context
        if (!result.error) {
            conversationHistory.set(user.id, {
                lastQuery: question,
                lastAnswer: result.answer || '',
                contexts: result.contexts || []
            });
        }
    }

    else if (commandName === 'clear') {
        if (conversationHistory.has(user.id)) {
            conversationHistory.delete(user.id);
            await interaction.reply({
                content: '✅ Your conversation history has been cleared!',
                ephemeral: true
            });
        } else {
            await interaction.reply({
                content: "ℹ️ You don't have any conversation history.",
                ephemeral: true
            });
        }
    }
});

// Handle @mentions
client.on('messageCreate', async (message) => {
    // Ignore messages from the bot itself
    if (message.author.bot) return;

    // Check if bot is mentioned
    if (message.mentions.has(client.user)) {
        // Extract the question (remove the mention)
        const question = message.content.replace(`<@${client.user.id}>`, '').trim();

        if (!question) {
            await message.channel.send(
                `Hi ${message.author}! Ask me a question using \`/ask\` or mention me with your question!`
            );
            return;
        }

        // Send "thinking" message
        const thinkingMsg = await message.channel.send('🤔 Thinking...');

        try {
            // Query the backend
            const result = await queryRagBackend(question);

            // Format response
            const responseText = formatResponse(result);

            // Edit the thinking message with the answer
            await thinkingMsg.edit(responseText);

            // Add feedback reactions
            await addFeedbackReactions(thinkingMsg);

            // Store conversation context
            if (!result.error) {
                conversationHistory.set(message.author.id, {
                    lastQuery: question,
                    lastAnswer: result.answer || '',
                    contexts: result.contexts || []
                });
            }
        } catch (error) {
            await thinkingMsg.edit(`❌ Sorry, something went wrong: ${error.message}`);
        }
    }
});

// Track feedback reactions
client.on('messageReactionAdd', async (reaction, user) => {
    // Ignore bot's own reactions
    if (user.bot) return;

    // Fetch partial reactions
    if (reaction.partial) {
        try {
            await reaction.fetch();
        } catch (error) {
            console.error('Error fetching reaction:', error);
            return;
        }
    }

    // Check if reaction is on bot's message
    if (reaction.message.author.id !== client.user.id) return;

    // Log feedback (extend this to save to a database)
    if (reaction.emoji.name === '👍') {
        console.log(`✅ Positive feedback from ${user.tag} on message: ${reaction.message.id}`);
    } else if (reaction.emoji.name === '👎') {
        console.log(`❌ Negative feedback from ${user.tag} on message: ${reaction.message.id}`);
    }
});

// Error handling
client.on('error', (error) => {
    console.error('Discord client error:', error);
});

// Login to Discord
if (!DISCORD_TOKEN) {
    console.error('❌ Error: DISCORD_TOKEN not found in environment variables!');
    console.error('Please create a .env file with your Discord bot token.');
    process.exit(1);
}

console.log('🚀 Starting Discord RAG Bot...');
client.login(DISCORD_TOKEN);