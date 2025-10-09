# query_house_api.py — 房屋交易 API 查詢腳本
# 功能：測試所有 API 端點並產生分析報告
# 執行：python query_house_api.py

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import json

# 設定
API_BASE = "http://127.0.0.1:8000"
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # 中文顯示
plt.rcParams['axes.unicode_minus'] = False  # 負號顯示

# ==================== API 查詢函數 ====================

def get_health():
    """取得系統健康狀態"""
    response = requests.get(f"{API_BASE}/health")
    return response.json()

def get_regions(city="NewTaipei", usage="住家用"):
    """取得所有區域資訊"""
    response = requests.get(
        f"{API_BASE}/regions",
        params={"city": city, "usage": usage}
    )
    return response.json()

def get_monthly_stats(city, district, usage="住家用"):
    """取得月均價統計"""
    response = requests.get(
        f"{API_BASE}/stats/monthly",
        params={"city": city, "district": district, "usage": usage}
    )
    return response.json()

def get_yearly_stats(city, district="ALL", usage="住家用"):
    """取得年均價統計"""
    response = requests.get(
        f"{API_BASE}/stats/yearly",
        params={"city": city, "district": district, "usage": usage}
    )
    return response.json()

def get_valuation(city, district, area_m2, usage="住家用"):
    """房屋估價"""
    response = requests.get(
        f"{API_BASE}/valuation",
        params={
            "city": city,
            "district": district,
            "area_m2": area_m2,
            "usage": usage
        }
    )
    return response.json()

# ==================== 分析功能 ====================

def print_health_report():
    """顯示系統健康報告"""
    print("=" * 80)
    print("🏥 系統健康檢查")
    print("=" * 80)
    
    try:
        health = get_health()
        print(f"✅ 狀態: {health['status']}")
        print(f"📊 總資料筆數: {health['rows']:,} 筆")
        print(f"📅 資料範圍: {health['date_range'][0]} ~ {health['date_range'][1]}")
        print(f"🏘️  新北市區域數: {health['districts_in_NewTaipei']} 個")
        
        if health['missing_districts']:
            print(f"⚠️  缺少的區域: {', '.join(health['missing_districts'])}")
        else:
            print("✅ 新北市 29 區資料完整")
        
        return health
    except Exception as e:
        print(f"❌ 無法連接 API: {e}")
        return None

def analyze_top_districts(top_n=10):
    """分析交易量最高的區域"""
    print(f"\n{'=' * 80}")
    print(f"📊 交易量 TOP {top_n} 區域")
    print("=" * 80)
    
    regions = get_regions()
    df = pd.DataFrame(regions)
    df = df.sort_values('n', ascending=False).head(top_n)
    
    print(f"\n{'排名':<5} {'區域':<15} {'交易筆數':<12} {'資料範圍'}")
    print("-" * 80)
    for idx, row in df.iterrows():
        print(f"{df.index.tolist().index(idx)+1:<5} {row['district']:<15} {row['n']:>10,} 筆  {row['min_date']} ~ {row['max_date']}")
    
    return df

def compare_districts(districts, save_chart=True):
    """比較多個區域的年均價"""
    print(f"\n{'=' * 80}")
    print(f"🔍 區域比較分析: {', '.join(districts)}")
    print("=" * 80)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    all_data = {}
    
    for district in districts:
        try:
            yearly = get_yearly_stats("NewTaipei", district)
            df = pd.DataFrame(yearly)
            all_data[district] = df
            
            # 繪製原始均價
            ax1.plot(df['year'], df['avg_raw'], marker='o', label=district, linewidth=2)
            
            # 繪製校正後均價
            ax2.plot(df['year'], df['avg_adj'], marker='s', label=district, linewidth=2)
            
            print(f"\n{district}:")
            print(f"  年份範圍: {df['year'].min()} ~ {df['year'].max()}")
            print(f"  平均原始單價: {df['avg_raw'].mean():.2f} 萬/坪")
            print(f"  平均校正單價: {df['avg_adj'].mean():.2f} 萬/坪")
            print(f"  總交易筆數: {df['n'].sum():,} 筆")
            
        except Exception as e:
            print(f"  ❌ {district} 查詢失敗: {e}")
    
    # 設定圖表
    ax1.set_title('原始年均價比較', fontsize=14, fontweight='bold')
    ax1.set_xlabel('年份')
    ax1.set_ylabel('萬元/坪')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.set_title('風險校正後年均價比較', fontsize=14, fontweight='bold')
    ax2.set_xlabel('年份')
    ax2.set_ylabel('萬元/坪')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_chart:
        filename = f"district_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"\n📊 圖表已儲存: {filename}")
    
    plt.show()
    
    return all_data

def plot_monthly_trend(district, save_chart=True):
    """繪製月均價趨勢圖"""
    print(f"\n{'=' * 80}")
    print(f"📈 {district} 月均價趨勢分析")
    print("=" * 80)
    
    try:
        monthly = get_monthly_stats("NewTaipei", district)
        df = pd.DataFrame(monthly)
        df['month'] = pd.to_datetime(df['month'])
        
        # 統計資訊
        print(f"\n資料月份數: {len(df)} 個月")
        print(f"時間範圍: {df['month'].min().date()} ~ {df['month'].max().date()}")
        print(f"原始均價範圍: {df['avg_raw'].min():.2f} ~ {df['avg_raw'].max():.2f} 萬/坪")
        print(f"校正均價範圍: {df['avg_adj'].min():.2f} ~ {df['avg_adj'].max():.2f} 萬/坪")
        print(f"平均月成交量: {df['n'].mean():.0f} 筆")
        
        # 繪圖
        fig, ax = plt.subplots(figsize=(14, 6))
        
        ax.plot(df['month'], df['avg_raw'], 
                marker='o', linewidth=2, label='原始均價', color='#667eea')
        ax.plot(df['month'], df['avg_adj'], 
                marker='s', linewidth=2, label='風險校正後均價', color='#f093fb')
        
        ax.set_title(f'{district} 月均價趨勢', fontsize=16, fontweight='bold')
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('萬元/坪', fontsize=12)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_chart:
            filename = f"{district}_monthly_trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"📊 圖表已儲存: {filename}")
        
        plt.show()
        
        return df
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        return None

def batch_valuation(district, areas=[50, 80, 100, 150]):
    """批次估價不同坪數的房屋"""
    print(f"\n{'=' * 80}")
    print(f"💰 {district} 批次估價")
    print("=" * 80)
    
    results = []
    
    print(f"\n{'面積(m²)':<12} {'面積(坪)':<12} {'每坪單價(萬)':<15} {'預估總價(萬)'}")
    print("-" * 80)
    
    for area in areas:
        try:
            valuation = get_valuation("NewTaipei", district, area)
            results.append(valuation)
            
            print(f"{valuation['area_m2']:<12} "
                  f"{valuation['area_ping']:<12.2f} "
                  f"{valuation['baseline_pp_ping']:<15,} "
                  f"{valuation['est_total']:>12,}")
            
        except Exception as e:
            print(f"{area:<12} 查詢失敗: {e}")
    
    return results

def export_to_excel(district, filename=None):
    """匯出區域完整資料到 Excel"""
    print(f"\n{'=' * 80}")
    print(f"📄 匯出 {district} 資料到 Excel")
    print("=" * 80)
    
    if filename is None:
        filename = f"{district}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    try:
        # 取得各種資料
        monthly = get_monthly_stats("NewTaipei", district)
        yearly = get_yearly_stats("NewTaipei", district)
        
        df_monthly = pd.DataFrame(monthly)
        df_yearly = pd.DataFrame(yearly)
        
        # 寫入 Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_monthly.to_excel(writer, sheet_name='月均價', index=False)
            df_yearly.to_excel(writer, sheet_name='年均價', index=False)
        
        print(f"✅ 已匯出: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ 匯出失敗: {e}")
        return None

# ==================== 互動式選單 ====================

def interactive_menu():
    """互動式選單"""
    print("\n" + "=" * 80)
    print("🏠 房屋交易分析系統 - 互動式查詢")
    print("=" * 80)
    
    # 先檢查系統狀態
    health = print_health_report()
    if not health:
        print("\n❌ 無法連接 API，請確認 app.py 是否正在運行")
        return
    
    districts = health['district_list']
    
    while True:
        print("\n" + "-" * 80)
        print("選擇功能:")
        print("  1. 查看交易量 TOP 10 區域")
        print("  2. 比較多個區域年均價")
        print("  3. 查看特定區域月均價趨勢")
        print("  4. 房屋估價（單次）")
        print("  5. 批次估價（多種坪數）")
        print("  6. 匯出區域資料到 Excel")
        print("  7. 查看所有區域列表")
        print("  0. 離開")
        print("-" * 80)
        
        choice = input("請輸入選項 (0-7): ").strip()
        
        if choice == "0":
            print("\n👋 再見！")
            break
            
        elif choice == "1":
            analyze_top_districts()
            
        elif choice == "2":
            print(f"\n可用區域: {', '.join(districts[:10])}... (共{len(districts)}個)")
            district_input = input("請輸入要比較的區域（用逗號分隔，例如: 板橋區,新莊區,中和區）: ")
            districts_to_compare = [d.strip() for d in district_input.split(",")]
            compare_districts(districts_to_compare)
            
        elif choice == "3":
            print(f"\n可用區域: {', '.join(districts[:10])}... (共{len(districts)}個)")
            district = input("請輸入區域名稱: ").strip()
            if district in districts:
                plot_monthly_trend(district)
            else:
                print(f"❌ 找不到區域: {district}")
                
        elif choice == "4":
            print(f"\n可用區域: {', '.join(districts[:10])}... (共{len(districts)}個)")
            district = input("請輸入區域名稱: ").strip()
            area = float(input("請輸入面積（平方公尺）: "))
            
            if district in districts:
                result = get_valuation("NewTaipei", district, area)
                print(f"\n{'=' * 60}")
                print(f"💰 估價結果")
                print(f"{'=' * 60}")
                print(f"區域: {result['district']}")
                print(f"面積: {result['area_m2']} m² ({result['area_ping']} 坪)")
                print(f"每坪單價: {result['baseline_pp_ping']:,} 萬")
                print(f"預估總價: {result['est_total']:,} 萬元")
                print(f"{'=' * 60}")
            else:
                print(f"❌ 找不到區域: {district}")
                
        elif choice == "5":
            print(f"\n可用區域: {', '.join(districts[:10])}... (共{len(districts)}個)")
            district = input("請輸入區域名稱: ").strip()
            
            if district in districts:
                batch_valuation(district)
            else:
                print(f"❌ 找不到區域: {district}")
                
        elif choice == "6":
            print(f"\n可用區域: {', '.join(districts[:10])}... (共{len(districts)}個)")
            district = input("請輸入區域名稱: ").strip()
            
            if district in districts:
                export_to_excel(district)
            else:
                print(f"❌ 找不到區域: {district}")
                
        elif choice == "7":
            print(f"\n{'=' * 80}")
            print(f"📋 所有可用區域 (共 {len(districts)} 個)")
            print(f"{'=' * 80}")
            for i, d in enumerate(districts, 1):
                print(f"{i:2d}. {d}", end="   ")
                if i % 5 == 0:
                    print()
            print("\n")
            
        else:
            print("❌ 無效的選項")

# ==================== 主程式 ====================

def main():
    """主程式"""
    print("=" * 80)
    print("🏠 房屋交易分析 API 測試腳本")
    print("=" * 80)
    print(f"API 端點: {API_BASE}")
    print("=" * 80)
    
    # 選擇模式
    print("\n選擇執行模式:")
    print("  1. 互動式選單（推薦）")
    print("  2. 完整示範（自動執行所有功能）")
    
    mode = input("\n請選擇 (1 或 2): ").strip()
    
    if mode == "1":
        interactive_menu()
    else:
        # 完整示範
        print("\n🚀 開始完整示範...\n")
        
        # 1. 系統健康檢查
        health = print_health_report()
        if not health:
            return
        
        # 2. TOP 10 區域
        top_districts = analyze_top_districts(10)
        
        # 3. 比較前3名區域
        top_3 = top_districts.head(3)['district'].tolist()
        print(f"\n比較 TOP 3 區域: {', '.join(top_3)}")
        compare_districts(top_3, save_chart=True)
        
        # 4. 詳細分析板橋區
        plot_monthly_trend("板橋區", save_chart=True)
        
        # 5. 板橋區批次估價
        batch_valuation("板橋區", areas=[50, 80, 100, 150])
        
        # 6. 匯出板橋區資料
        export_to_excel("板橋區")
        
        print("\n" + "=" * 80)
        print("✅ 完整示範結束！")
        print("=" * 80)

if __name__ == "__main__":
    main()