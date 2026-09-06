package main

import (
	"fmt"
	"os"
)

func main() {
	goprivate := os.Getenv("GOPRIVATE")
	gonosumb := os.Getenv("GONOSUMDB")
	
	fmt.Println("=== Go 环境变量配置测试 ===")
	fmt.Printf("GOPRIVATE: %s\n", goprivate)
	fmt.Printf("GONOSUMDB: %s\n", gonosumb)
	
	if goprivate == "" {
		fmt.Println("\n❌ 错误: GOPRIVATE 未设置")
		return
	}
	
	expected := "*.byted.org,*.everphoto.cn,git.smartisan.com"
	if goprivate != expected {
		fmt.Printf("\n❌ 错误: GOPRIVATE 值不正确\n")
		fmt.Printf("期望: %s\n", expected)
		fmt.Printf("实际: %s\n", goprivate)
		return
	}
	
	fmt.Println("\n✅ 成功: GOPRIVATE 配置正确")
	
	if gonosumb == "" {
		fmt.Println("⚠️  警告: GONOSUMDB 未设置（可选）")
	} else if gonosumb != expected {
		fmt.Printf("\n❌ 错误: GONOSUMDB 值不正确\n")
		fmt.Printf("期望: %s\n", expected)
		fmt.Printf("实际: %s\n", gonosumb)
		return
	} else {
		fmt.Println("✅ 成功: GONOSUMDB 配置正确")
	}
}