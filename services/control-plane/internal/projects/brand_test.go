package projects

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// PC-020: a brand change goes to the project's workspace, and a rename renames the project too.
func TestABrandRenameRenamesTheProject(t *testing.T) {
	studio := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasSuffix(r.URL.Path, "/brand") {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		_, _ = w.Write([]byte(`{"changed":["name"],"brand":{"name":"Kaari Studio"}}`))
	}))
	defer studio.Close()
	pStore := newFakeProjectStore()
	server, id := creditServerWithStore(t, pStore, studio.URL)

	req, _ := http.NewRequest(http.MethodPost, server.URL+"/projects/"+id+"/brand", strings.NewReader(`{"name":"Kaari Studio"}`))
	req.Header.Set("Authorization", testBearer)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status %d", resp.StatusCode)
	}
	project, _ := pStore.GetProject(context.Background(), id, "usr-credit")
	if project.Name != "Kaari Studio" {
		t.Errorf("project name %q, want Kaari Studio", project.Name)
	}

	other, _ := http.NewRequest(http.MethodGet, server.URL+"/projects/not-mine/brand", nil)
	other.Header.Set("Authorization", testBearer)
	resp, err = http.DefaultClient.Do(other)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("someone else's project: status %d, want 404", resp.StatusCode)
	}
}
