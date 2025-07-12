-- ====================================================================
-- Shiosayi Backend Seed Data
-- ====================================================================
-- This script clears existing data and populates the database
-- with a set of dummy guardians and films for testing purposes.
--
-- How to use:
-- 1. Make sure your database file exists (e.g., 'shiosayi.db').
-- 2. Run the command: sqlite3 shiosayi.db < seed.sql
-- ====================================================================


-- =============================
-- Step 1: Clear existing data
-- =============================
-- This prevents duplicating data if the script is run multiple times.
DELETE FROM films;
DELETE FROM guardians;
DELETE FROM suggestions;
DELETE FROM kofi_events;


-- =============================
-- Step 2: Populate 'guardians'
-- =============================

-- The primary admin/developer guardian as requested.
INSERT INTO guardians (id, name, email, tier, token, joined_at) VALUES
('g001', 'bugswriter', 'suraj@bugswriter.com', 'savior', 'shio_admin_3K8dG9sFpW7jZtQyR4xHn2bA5cV6mB', '2024-01-01 10:00:00');

-- Add other random guardians for variety.
INSERT INTO guardians (id, name, email, tier, token, joined_at) VALUES
('g002', 'Aria Keeper', 'aria.k@example.com', 'keeper', 'shio_token_keeper_aria123', '2024-02-15 12:30:00'),
('g003', 'Ben Lover', 'ben.lover@example.com', 'lover', 'shio_token_lover_ben456', '2024-03-20 18:00:00'),
('g004', 'Chloe Patron', 'chloe.p@example.com', 'lover', 'shio_token_patron_chloe789', '2024-04-05 09:00:00');


-- =============================
-- Step 3: Populate 'films'
-- =============================
-- We will add a mix of adopted, orphan, and abandoned films.

INSERT INTO films (title, year, plot, poster_url, region, guardian_id, status, magnet, updated_at) VALUES
-- Films Adopted by 'bugswriter' (g001, Savior Tier)
('Spirited Away', 2001, 'A young girl wanders into a world of spirits, gods, and monsters.', 'https://image.tmdb.org/t/p/w500/39wmItIW2zwAtoO70iE3d236F6I.jpg', 'Japan', 'g001', 'adopted', 'magnet:?xt=urn:btih:spiritedawayhash', '2024-05-01 11:00:00'),
('Akira', 1988, 'A secret military project endangers Neo-Tokyo when it turns a biker gang member into a rampaging psychic psychopath.', 'https://image.tmdb.org/t/p/w500/5dYtA1a30s1hB4Hk2SAnH1a9j2u.jpg', 'Japan', 'g001', 'adopted', 'magnet:?xt=urn:btih:akirahash', '2024-05-02 12:00:00'),
('Oldboy', 2003, 'After being kidnapped and imprisoned for fifteen years, a desperate man seeks vengeance on his captor.', 'https://image.tmdb.org/t/p/w500/pWDt3Tj0k9I0sAk4L284K32T1p.jpg', 'South Korea', 'g001', 'adopted', 'magnet:?xt=urn:btih:oldboyhash', '2024-05-03 13:00:00'),

-- Film Adopted by 'Aria Keeper' (g002, Keeper Tier)
('My Neighbor Totoro', 1988, 'Two young sisters encounter a friendly, magical forest spirit in postwar rural Japan.', 'https://image.tmdb.org/t/p/w500/rtGDOeG9Lzoerk0Q46eKxW7I1p8.jpg', 'Japan', 'g002', 'adopted', 'magnet:?xt=urn:btih:totorohash', '2024-04-20 14:00:00'),

-- Film Adopted by 'Ben Lover' (g003, Lover Tier)
('Your Name.', 2016, 'Two strangers find themselves linked in a bizarre way when they start swapping bodies.', 'https://image.tmdb.org/t/p/w500/q719jXXEzOoYaps6babgKnONONX.jpg', 'Japan', 'g003', 'adopted', 'magnet:?xt=urn:btih:yournamehash', '2024-04-25 15:00:00'),

-- Orphan Films (Available for adoption)
('Princess Mononoke', 1997, 'A prince embroiled in a struggle between forest gods and the humans who consume their resources.', 'https://image.tmdb.org/t/p/w500/gzb6P78zeFTnv9eoFYnaJ2n8Saa.jpg', 'Japan', NULL, 'orphan', 'magnet:?xt=urn:btih:mononokehash', '2024-01-10 00:00:00'),
('Parasite', 2019, 'Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.', 'https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg', 'South Korea', NULL, 'orphan', 'magnet:?xt=urn:btih:parasitehash', '2024-01-11 00:00:00'),
('Grave of the Fireflies', 1988, 'A young boy and his little sister struggle to survive in Japan during World War II.', 'https://image.tmdb.org/t/p/w500/40U4E2u5u2G2a2d2t2y2p1S31d.jpg', 'Japan', NULL, 'orphan', 'magnet:?xt=urn:btih:fireflieshash', '2024-01-12 00:00:00'),
('Perfect Blue', 1997, 'A retired pop singer turned actress has her sense of reality shattered when she is stalked by an obsessed fan and seemingly haunted by her past.', 'https://image.tmdb.org/t/p/w500/38gH3xQ8gT9iJd23nJ3A1vjWlPa.jpg', 'Japan', NULL, 'orphan', 'magnet:?xt=urn:btih:perfectbluehash', '2024-01-13 00:00:00'),

-- Abandoned Film (Available for adoption)
('Paprika', 2006, 'A research psychologist enters the dream world to find a stolen device that allows others to do the same.', 'https://image.tmdb.org/t/p/w500/tK1jRGyPgr298pBgjJb9k0i1s3w.jpg', 'Japan', NULL, 'abandoned', NULL, '2024-02-01 00:00:00');


-- =============================
-- End of Seed Script
-- =============================
