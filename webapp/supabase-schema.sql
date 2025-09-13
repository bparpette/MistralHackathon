-- Schema Supabase pour le système de mémoire collective multi-tenant

-- Table des équipes
CREATE TABLE teams (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    team_token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table des utilisateurs
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    user_token VARCHAR(255) UNIQUE NOT NULL,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table des mémoires (pour tracking et analytics)
CREATE TABLE memories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    memory_id VARCHAR(255) NOT NULL, -- ID de la mémoire dans Qdrant
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les performances
CREATE INDEX idx_users_team_id ON users(team_id);
CREATE INDEX idx_users_user_token ON users(user_token);
CREATE INDEX idx_teams_team_token ON teams(team_token);
CREATE INDEX idx_memories_team_id ON memories(team_id);
CREATE INDEX idx_memories_user_id ON memories(user_id);

-- Fonction pour générer des tokens uniques
CREATE OR REPLACE FUNCTION generate_team_token() RETURNS TEXT AS $$
BEGIN
    RETURN 'team_' || encode(gen_random_bytes(16), 'hex');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_user_token() RETURNS TEXT AS $$
BEGIN
    RETURN 'user_' || encode(gen_random_bytes(16), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Trigger pour générer automatiquement les tokens
CREATE OR REPLACE FUNCTION set_team_token() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.team_token IS NULL OR NEW.team_token = '' THEN
        NEW.team_token := generate_team_token();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_user_token() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_token IS NULL OR NEW.user_token = '' THEN
        NEW.user_token := generate_user_token();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_team_token
    BEFORE INSERT ON teams
    FOR EACH ROW
    EXECUTE FUNCTION set_team_token();

CREATE TRIGGER trigger_set_user_token
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_user_token();

-- RLS (Row Level Security) pour la sécurité
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

-- Politiques RLS pour les équipes
CREATE POLICY "Teams are viewable by team members" ON teams
    FOR SELECT USING (
        id IN (
            SELECT team_id FROM users 
            WHERE user_token = current_setting('request.jwt.claims', true)::json->>'user_token'
        )
    );

-- Politiques RLS pour les utilisateurs
CREATE POLICY "Users can view team members" ON users
    FOR SELECT USING (
        team_id IN (
            SELECT team_id FROM users 
            WHERE user_token = current_setting('request.jwt.claims', true)::json->>'user_token'
        )
    );

-- Politiques RLS pour les mémoires
CREATE POLICY "Users can view team memories" ON memories
    FOR SELECT USING (
        team_id IN (
            SELECT team_id FROM users 
            WHERE user_token = current_setting('request.jwt.claims', true)::json->>'user_token'
        )
    );

-- Fonction pour vérifier un token utilisateur (utilisée par le MCP)
CREATE OR REPLACE FUNCTION verify_user_token(token TEXT)
RETURNS TABLE(
    user_id UUID,
    team_id UUID,
    team_token TEXT,
    user_name TEXT,
    user_role TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id,
        u.team_id,
        t.team_token,
        u.name,
        u.role
    FROM users u
    JOIN teams t ON u.team_id = t.id
    WHERE u.user_token = token;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Données de test (optionnel)
INSERT INTO teams (name) VALUES 
    ('Équipe Alpha'),
    ('Équipe Beta'),
    ('Équipe Gamma');

-- Insérer des utilisateurs de test
INSERT INTO users (email, name, team_id, role) VALUES 
    ('alice@example.com', 'Alice CEO', (SELECT id FROM teams WHERE name = 'Équipe Alpha'), 'admin'),
    ('bob@example.com', 'Bob CTO', (SELECT id FROM teams WHERE name = 'Équipe Alpha'), 'member'),
    ('charlie@example.com', 'Charlie CS', (SELECT id FROM teams WHERE name = 'Équipe Alpha'), 'member');
