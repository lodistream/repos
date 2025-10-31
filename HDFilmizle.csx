// ==CloudStreamScript==
// @name HDFilmizle
// @description HDFilmizle.to – Türkçe Dublaj ve Altyazılı Film/Dizi İzle
// @author GitLatte
// @language tr
// @version 1.1.0
// @compatibleVersion 4.6.0
// @supportedTypes movie, tvseries
// @homepage https://www.hdfilmizle.to
// ==/CloudStreamScript==

package com.lagradost.script

import com.lagradost.cloudstream3.*
import com.lagradost.cloudstream3.utils.*
import com.lagradost.cloudstream3.extractors.*
import com.lagradost.cloudstream3.mvvm.safeApiCall
import org.jsoup.nodes.Element

class HDFilmizle : MainAPI() {
    override var mainUrl = "https://www.hdfilmizle.to"
    override var name = "HDFilmizle"
    override val supportedTypes = setOf(TvType.Movie, TvType.TvSeries)
    override var lang = "tr"

    override suspend fun getMainPage(page: Int, request: MainPageRequest): HomePageResponse {
        val home = ArrayList<HomePageList>()
        try {
            val doc = app.get(mainUrl).document

            val popFilmler = doc.select("div.tab-pane.active div.item")
                .mapNotNull { it.toSearchResult() }
            if (popFilmler.isNotEmpty()) home.add(HomePageList("Popüler Filmler", popFilmler))

            val yeniFilmler = app.get("$mainUrl/film-izle").document
                .select("div.movie-poster").mapNotNull { it.toSearchResult() }
            if (yeniFilmler.isNotEmpty()) home.add(HomePageList("Yeni Filmler", yeniFilmler))

            val popDiziler = app.get("$mainUrl/dizi-izle").document
                .select("div.movie-poster").mapNotNull { it.toSearchResult() }
            if (popDiziler.isNotEmpty()) home.add(HomePageList("Popüler Diziler", popDiziler))

        } catch (e: Exception) {
            logError(e)
        }
        return HomePageResponse(home)
    }

    override suspend fun search(query: String): List<SearchResponse> {
        return safeApiCall {
            val encoded = java.net.URLEncoder.encode(query, "UTF-8")
            val doc = app.get("$mainUrl/ara?q=$encoded").document
            doc.select("div.movie-poster, div.item").mapNotNull { it.toSearchResult() }
        } ?: emptyList()
    }

    override suspend fun load(url: String): LoadResponse? {
        return safeApiCall {
            val doc = app.get(url).document
            val title = doc.selectFirst("h1.film-title")?.text() ?: return@safeApiCall null
            val desc = doc.selectFirst("div.film-about p")?.text()
            val poster = doc.selectFirst("div.film-poster img")?.attr("src")
            val year = doc.selectFirst("span.film-year")?.text()?.toIntOrNull()
            val rating = doc.selectFirst("span.imdb-rating")?.text()?.toRatingInt()

            val episodes = doc.select("div.episode-list a")
            val isSeries = doc.selectFirst("div.seasons") != null || episodes.isNotEmpty()

            if (!isSeries) {
                newMovieLoadResponse(title, url, TvType.Movie) {
                    this.posterUrl = fixUrl(poster)
                    this.plot = desc
                    this.year = year
                    this.rating = rating
                }
            } else {
                val epList = episodes.mapNotNull { ep ->
                    val epUrl = ep.attr("href")
                    val epName = ep.selectFirst("span.episode-name")?.text()
                        ?: "Bölüm ${ep.selectFirst("span.episode-number")?.text()}"
                    newEpisode(epUrl) {
                        this.name = epName
                        this.posterUrl = fixUrl(poster)
                    }
                }

                newTvSeriesLoadResponse(title, url, TvType.TvSeries, epList) {
                    this.posterUrl = fixUrl(poster)
                    this.plot = desc
                    this.year = year
                    this.rating = rating
                }
            }
        }
    }

    override suspend fun loadLinks(
        data: String,
        isCasting: Boolean,
        subtitleCallback: (SubtitleFile) -> Unit,
        callback: (ExtractorLink) -> Unit
    ): Boolean {
        return safeApiCall {
            val doc = app.get(data).document

            // iframe player’lar
            doc.select("iframe[src]").forEach {
                val iframeUrl = it.attr("src")
                if (iframeUrl.isNotBlank())
                    loadExtractor(iframeUrl, mainUrl, subtitleCallback, callback)
            }

            // script içi video bağlantıları
            doc.select("script:containsData(video)").forEach { script ->
                val text = script.data()
                Regex("""(https?:[^"'\s]+?\.(mp4|m3u8)[^"'\s]*)""").findAll(text).forEach { m ->
                    callback(
                        ExtractorLink(
                            name,
                            "Direct",
                            m.value,
                            mainUrl,
                            Qualities.Unknown.value
                        )
                    )
                }
            }
            true
        } ?: false
    }

    private fun Element.toSearchResult(): SearchResponse? {
        val title = this.selectFirst("img")?.attr("alt")
            ?: this.selectFirst("h3, h4")?.text() ?: return null
        val href = this.selectFirst("a")?.attr("href") ?: return null
        val poster = this.selectFirst("img")?.attr("src")
        val year = this.selectFirst("span.year")?.text()?.toIntOrNull()
        val isSeries = href.contains("/dizi/") ||
            this.selectFirst("span.type")?.text()?.contains("dizi", true) == true

        return if (isSeries)
            newTvSeriesSearchResponse(title, fixUrl(href)) {
                this.posterUrl = fixUrl(poster)
                this.year = year
            }
        else
            newMovieSearchResponse(title, fixUrl(href)) {
                this.posterUrl = fixUrl(poster)
                this.year = year
            }
    }

    private fun fixUrl(url: String?): String? {
        if (url == null) return null
        return when {
            url.startsWith("//") -> "https:$url"
            url.startsWith("/") -> "$mainUrl$url"
            !url.startsWith("http") -> "$mainUrl/$url"
            else -> url
        }
    }

    private fun String?.toRatingInt(): Int? =
        this?.replace(",", ".")?.toFloatOrNull()?.times(10)?.toInt()
}
