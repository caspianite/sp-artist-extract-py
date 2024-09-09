--
-- PostgreSQL database dump
--

-- Dumped from database version 14.11 (Ubuntu 14.11-1.pgdg20.04+1)
-- Dumped by pg_dump version 15.3

-- Started on 2024-09-09 02:25:48

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 8 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO postgres;

--
-- TOC entry 3855 (class 0 OID 0)
-- Dependencies: 8
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- TOC entry 598 (class 1255 OID 9927951)
-- Name: rows_inserted_rate(text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.rows_inserted_rate(table_name text, timestamp_column text) RETURNS TABLE(inserts_per_second numeric, inserts_per_minute numeric)
    LANGUAGE plpgsql
    AS $$
DECLARE
    sql_query text;
BEGIN
    -- Construct the dynamic SQL query for inserts per second
    sql_query := format('
        SELECT
            -- Count the number of rows inserted in the last second
            (SELECT COUNT(*) FROM %I WHERE %I >= NOW() - INTERVAL ''1 second'') AS inserts_per_second,
            
            -- Count the number of rows inserted in the last minute
            (SELECT COUNT(*) FROM %I WHERE %I >= NOW() - INTERVAL ''1 minute'') AS inserts_per_minute
        ', table_name, timestamp_column, table_name, timestamp_column);

    -- Execute the dynamic SQL query and return the result
    RETURN QUERY EXECUTE sql_query;
END;
$$;


ALTER FUNCTION public.rows_inserted_rate(table_name text, timestamp_column text) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 234 (class 1259 OID 9927094)
-- Name: artist_performance_over_time; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.artist_performance_over_time (
    "time" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    artist_key text NOT NULL,
    world_rank integer NOT NULL,
    monthly_listeners bigint NOT NULL,
    monthly_listeners_delta bigint NOT NULL
);


ALTER TABLE public.artist_performance_over_time OWNER TO postgres;

--
-- TOC entry 288 (class 1259 OID 9928529)
-- Name: albums; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.albums (
    time_release timestamp with time zone NOT NULL,
    album_key text NOT NULL,
    artist_key text NOT NULL,
    name text NOT NULL,
    label text,
    tracks_count integer NOT NULL,
    pathfinder_json jsonb NOT NULL,
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.albums OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 42868)
-- Name: artist_entry_id; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.artist_entry_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.artist_entry_id OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 43136)
-- Name: artist_information; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.artist_information (
    artist_key text NOT NULL,
    artist_pathfinder_json jsonb NOT NULL,
    llm_description_summary_json jsonb,
    artist_entry_id integer NOT NULL,
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.artist_information OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 42872)
-- Name: artist_json; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.artist_json (
    artist_key text NOT NULL,
    artist_data_json jsonb NOT NULL,
    artist_entry_id integer DEFAULT nextval('public.artist_entry_id'::regclass) NOT NULL,
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.artist_json OWNER TO postgres;

--
-- TOC entry 290 (class 1259 OID 9928553)
-- Name: pathfinder_ids; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pathfinder_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pathfinder_ids OWNER TO postgres;

--
-- TOC entry 291 (class 1259 OID 9928554)
-- Name: artist_pathfinder_over_time; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.artist_pathfinder_over_time (
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    artist_key text NOT NULL,
    pathfinder_id bigint DEFAULT nextval('public.pathfinder_ids'::regclass) NOT NULL,
    stats jsonb NOT NULL,
    profile jsonb NOT NULL,
    goods jsonb NOT NULL,
    relatedcontent jsonb NOT NULL,
    relatedartists jsonb NOT NULL,
    discography jsonb NOT NULL,
    relatedvideos jsonb NOT NULL
);


ALTER TABLE public.artist_pathfinder_over_time OWNER TO postgres;

--
-- TOC entry 292 (class 1259 OID 9928561)
-- Name: relation_n; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.relation_n
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.relation_n OWNER TO postgres;

--
-- TOC entry 293 (class 1259 OID 9928562)
-- Name: artist_relations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.artist_relations (
    artist_key text NOT NULL,
    relates_to_artist_key text NOT NULL,
    relation_id text NOT NULL,
    relation_n bigint DEFAULT nextval('public.relation_n'::regclass) NOT NULL,
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.artist_relations OWNER TO postgres;

--
-- TOC entry 285 (class 1259 OID 9928413)
-- Name: errors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.errors (
    "time" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    error jsonb NOT NULL
);


ALTER TABLE public.errors OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 8520190)
-- Name: linked_artist_information; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.linked_artist_information (
    artist_key text NOT NULL,
    artist_pathfinder_json jsonb NOT NULL,
    llm_description_summary_json jsonb,
    artist_entry_id integer NOT NULL,
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.linked_artist_information OWNER TO postgres;

--
-- TOC entry 283 (class 1259 OID 9927967)
-- Name: notes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notes (
    artist_key text NOT NULL,
    note text,
    "time" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.notes OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 42887)
-- Name: proxies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proxies (
    protocol text DEFAULT 'http'::text NOT NULL,
    host text NOT NULL,
    auth jsonb,
    port text NOT NULL
);


ALTER TABLE public.proxies OWNER TO postgres;

--
-- TOC entry 287 (class 1259 OID 9928512)
-- Name: proxies_urls; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proxies_urls (
    url text NOT NULL
);


ALTER TABLE public.proxies_urls OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 42863)
-- Name: spcookies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.spcookies (
    sp_dc text NOT NULL,
    sp_key text NOT NULL
);


ALTER TABLE public.spcookies OWNER TO postgres;

--
-- TOC entry 289 (class 1259 OID 9928537)
-- Name: tracks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tracks (
    scraped_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    track_key text NOT NULL,
    album_key text NOT NULL,
    name text NOT NULL,
    playcount bigint NOT NULL,
    artists jsonb NOT NULL,
    content_rating jsonb NOT NULL
);


ALTER TABLE public.tracks OWNER TO postgres;

--
-- TOC entry 3690 (class 2606 OID 9928535)
-- Name: albums albums_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.albums
    ADD CONSTRAINT albums_pkey PRIMARY KEY (album_key);


--
-- TOC entry 3680 (class 2606 OID 43143)
-- Name: artist_information artist_information_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artist_information
    ADD CONSTRAINT artist_information_pkey PRIMARY KEY (artist_key);


--
-- TOC entry 3675 (class 2606 OID 42879)
-- Name: artist_json artist_json_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artist_json
    ADD CONSTRAINT artist_json_pkey PRIMARY KEY (artist_key);


--
-- TOC entry 3694 (class 2606 OID 9928570)
-- Name: artist_relations artist_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artist_relations
    ADD CONSTRAINT artist_relations_pkey PRIMARY KEY (relation_n);


--
-- TOC entry 3678 (class 2606 OID 42894)
-- Name: proxies proxies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT proxies_pkey PRIMARY KEY (host);


--
-- TOC entry 3688 (class 2606 OID 9928518)
-- Name: proxies_urls proxies_urls_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proxies_urls
    ADD CONSTRAINT proxies_urls_pkey PRIMARY KEY (url);


--
-- TOC entry 3673 (class 2606 OID 42886)
-- Name: spcookies spcookies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spcookies
    ADD CONSTRAINT spcookies_pkey PRIMARY KEY (sp_key);


--
-- TOC entry 3692 (class 2606 OID 9928544)
-- Name: tracks tracks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tracks
    ADD CONSTRAINT tracks_pkey PRIMARY KEY (track_key);


--
-- TOC entry 3686 (class 1259 OID 9927897)
-- Name: artist_performance_over_time_time_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX artist_performance_over_time_time_idx ON public.artist_performance_over_time USING btree ("time" DESC);


--
-- TOC entry 3681 (class 1259 OID 8520189)
-- Name: idx_artist_information_jsonb_artist_pathfinder_json_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_artist_information_jsonb_artist_pathfinder_json_gin ON public.artist_information USING gin (artist_pathfinder_json);


--
-- TOC entry 3676 (class 1259 OID 43135)
-- Name: idx_artist_json; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_artist_json ON public.artist_json USING btree (artist_key, artist_data_json, artist_entry_id, scraped_at);


--
-- TOC entry 3682 (class 1259 OID 9903740)
-- Name: idx_artist_key_linked_artist_information; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_artist_key_linked_artist_information ON public.linked_artist_information USING btree (artist_key);


--
-- TOC entry 3683 (class 1259 OID 9903733)
-- Name: idx_linked_artist_information_jsonb_artist_pathfinder_json_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_linked_artist_information_jsonb_artist_pathfinder_json_gin ON public.linked_artist_information USING gin (artist_pathfinder_json);


--
-- TOC entry 3684 (class 1259 OID 9909630)
-- Name: idx_linked_artist_information_jsonb_llm_description_summary_jso; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_linked_artist_information_jsonb_llm_description_summary_jso ON public.linked_artist_information USING gin (llm_description_summary_json);


--
-- TOC entry 3685 (class 1259 OID 9909631)
-- Name: idx_linked_artist_information_llm_description_summary_json; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_linked_artist_information_llm_description_summary_json ON public.linked_artist_information USING gin (llm_description_summary_json);


--
-- TOC entry 3695 (class 2620 OID 9927896)
-- Name: artist_performance_over_time ts_insert_blocker; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.artist_performance_over_time FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- TOC entry 3856 (class 0 OID 0)
-- Dependencies: 8
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;
GRANT USAGE ON SCHEMA public TO clouedoc;


--
-- TOC entry 3857 (class 0 OID 0)
-- Dependencies: 234
-- Name: TABLE artist_performance_over_time; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.artist_performance_over_time TO clouedoc;


--
-- TOC entry 3858 (class 0 OID 0)
-- Dependencies: 288
-- Name: TABLE albums; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.albums TO clouedoc;


--
-- TOC entry 3859 (class 0 OID 0)
-- Dependencies: 227
-- Name: SEQUENCE artist_entry_id; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.artist_entry_id TO clouedoc;


--
-- TOC entry 3860 (class 0 OID 0)
-- Dependencies: 232
-- Name: TABLE artist_information; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.artist_information TO clouedoc;


--
-- TOC entry 3861 (class 0 OID 0)
-- Dependencies: 228
-- Name: TABLE artist_json; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.artist_json TO clouedoc;


--
-- TOC entry 3862 (class 0 OID 0)
-- Dependencies: 290
-- Name: SEQUENCE pathfinder_ids; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.pathfinder_ids TO clouedoc;


--
-- TOC entry 3863 (class 0 OID 0)
-- Dependencies: 291
-- Name: TABLE artist_pathfinder_over_time; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.artist_pathfinder_over_time TO clouedoc;


--
-- TOC entry 3864 (class 0 OID 0)
-- Dependencies: 292
-- Name: SEQUENCE relation_n; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.relation_n TO clouedoc;


--
-- TOC entry 3865 (class 0 OID 0)
-- Dependencies: 293
-- Name: TABLE artist_relations; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.artist_relations TO clouedoc;


--
-- TOC entry 3866 (class 0 OID 0)
-- Dependencies: 285
-- Name: TABLE errors; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.errors TO clouedoc;


--
-- TOC entry 3867 (class 0 OID 0)
-- Dependencies: 233
-- Name: TABLE linked_artist_information; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.linked_artist_information TO clouedoc;


--
-- TOC entry 3868 (class 0 OID 0)
-- Dependencies: 283
-- Name: TABLE notes; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.notes TO clouedoc;


--
-- TOC entry 3869 (class 0 OID 0)
-- Dependencies: 229
-- Name: TABLE proxies; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.proxies TO clouedoc;


--
-- TOC entry 3870 (class 0 OID 0)
-- Dependencies: 287
-- Name: TABLE proxies_urls; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.proxies_urls TO clouedoc;


--
-- TOC entry 3871 (class 0 OID 0)
-- Dependencies: 226
-- Name: TABLE spcookies; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.spcookies TO clouedoc;


--
-- TOC entry 3872 (class 0 OID 0)
-- Dependencies: 289
-- Name: TABLE tracks; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.tracks TO clouedoc;


--
-- TOC entry 2538 (class 826 OID 9909007)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES  TO clouedoc;


--
-- TOC entry 2537 (class 826 OID 9909006)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES  TO clouedoc;


-- Completed on 2024-09-09 02:25:53

--
-- PostgreSQL database dump complete
--

