package main

import (
	. "gopkg.in/check.v1"
	"testing"
)

func Test(t *testing.T) { TestingT(t) }

type TestClient struct{}

var _ = Suite(&TestClient{})

func (s *TestClient) TestDiscovery(c *C) {
	checksums_filenames := Discover("test_files/")
	c.Assert(len(checksums_filenames), Equals, 2)
}
