// Package config loads simple INI configuration files for the services.
//
// Resolution precedence for every value is:
//
//	environment variable  >  config.ini value  >  built-in default
//
// so cloud deployments can keep injecting settings via env/Secrets Manager
// while local runs can rely entirely on config.ini. No third-party deps.
package config

import (
	"bufio"
	"os"
	"path/filepath"
	"strings"
)

// Config holds parsed INI data as section -> key -> value (all lower-cased).
type Config struct {
	Path string
	data map[string]map[string]string
}

// Load searches for an INI file and parses it. Candidate paths, in order:
//
//	1. explicit path (e.g. from a -config flag), if non-empty
//	2. $CONFIG_FILE
//	3. ./config.ini (current working directory)
//	4. config.ini next to the executable
//
// A missing file is not an error: an empty Config is returned so the service
// can still run purely from environment variables.
func Load(explicit string) *Config {
	candidates := []string{}
	if explicit != "" {
		candidates = append(candidates, explicit)
	}
	if env := os.Getenv("CONFIG_FILE"); env != "" {
		candidates = append(candidates, env)
	}
	candidates = append(candidates, "config.ini")
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "config.ini"))
	}

	for _, p := range candidates {
		if f, err := os.Open(p); err == nil {
			defer f.Close()
			return &Config{Path: p, data: parse(f)}
		}
	}
	return &Config{data: map[string]map[string]string{}}
}

func parse(f *os.File) map[string]map[string]string {
	data := map[string]map[string]string{}
	section := ""
	data[section] = map[string]string{}

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
			continue
		}
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			section = strings.ToLower(strings.TrimSpace(line[1 : len(line)-1]))
			if _, ok := data[section]; !ok {
				data[section] = map[string]string{}
			}
			continue
		}
		eq := strings.IndexAny(line, "=:")
		if eq < 0 {
			continue
		}
		key := strings.ToLower(strings.TrimSpace(line[:eq]))
		val := strings.TrimSpace(line[eq+1:])
		val = strings.Trim(val, `"'`) // strip optional surrounding quotes
		data[section][key] = val
	}
	return data
}

// Get returns the raw INI value for a section/key and whether it was present.
func (c *Config) Get(section, key string) (string, bool) {
	if c == nil {
		return "", false
	}
	sec, ok := c.data[strings.ToLower(section)]
	if !ok {
		return "", false
	}
	v, ok := sec[strings.ToLower(key)]
	return v, ok
}

// Value resolves a setting using the documented precedence:
// env var, then config.ini [section] key, then the provided default.
func (c *Config) Value(envKey, section, key, def string) string {
	if envKey != "" {
		if v := os.Getenv(envKey); v != "" {
			return v
		}
	}
	if v, ok := c.Get(section, key); ok && v != "" {
		return v
	}
	return def
}
